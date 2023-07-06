package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/confluentinc/confluent-kafka-go/kafka"
	_ "github.com/lib/pq"
)

// InputMessage represents the JSON message structure for input.
type InputMessage struct {
	Numbers []int `json:"numbers"`
	Sum     int   `json:"sum"`
	Product int   `json:"product"`
}

// OutputMessage represents the JSON message structure for output.
type OutputMessage struct {
	Numbers []int `json:"numbers"`
	Sum     int   `json:"sum"`
	Product int   `json:"product"`
	LCM     int   `json:"lcm"`
}

func main() {
	// Check if required environment variables are set
	requiredEnvVars := []string{"DB_USER", "DB_PASSWORD"}
	missingVars := []string{}
	for _, envVar := range requiredEnvVars {
		if os.Getenv(envVar) == "" {
			missingVars = append(missingVars, envVar)
		}
	}

	if len(missingVars) > 0 {
		log.Printf("Missing required environment variables: %s", strings.Join(missingVars, ", "))
		os.Exit(1)
	}

	bootstrapServers := getEnv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9002")
	inputTopic := getEnv("KAFKA_TOPIC_INPUT", "stage3")
	outputTopic := getEnv("KAFKA_TOPIC_OUTPUT", "stage4")
	dbHost := getEnv("DB_HOST", "localhost")
	dbPort := getEnv("DB_PORT", "5432")
	dbName := getEnv("DB_NAME", "stage")
	dbUser := os.Getenv("DB_USER")
	dbPassword := os.Getenv("DB_PASSWORD")

	consumer, err := kafka.NewConsumer(&kafka.ConfigMap{
		"bootstrap.servers": bootstrapServers,
		"group.id":          "stage3",
		"auto.offset.reset": "earliest",
	})
	if err != nil {
		log.Fatalf("Failed to create consumer: %v", err)
	}
	defer consumer.Close()

	producer, err := kafka.NewProducer(&kafka.ConfigMap{
		"bootstrap.servers": bootstrapServers,
	})
	if err != nil {
		log.Fatalf("Failed to create producer: %v", err)
	}
	defer producer.Close()

	// Connect to the Postgres database
	dbInfo := fmt.Sprintf("host=%s port=%s dbname=%s user=%s password=%s sslmode=disable", dbHost, dbPort, dbName, dbUser, dbPassword)
	db, err := sql.Open("postgres", dbInfo)
	if err != nil {
		log.Fatalf("Failed to connect to the database: %v", err)
	}
	defer db.Close()

	//Ensure the table exists
	err = createTableIfNotExists(db)
	if err != nil {
		log.Fatalf("Failed to create table: %v", err)
	}

	// Subscribe to the input topic
	err = consumer.SubscribeTopics([]string{inputTopic}, nil)
	if err != nil {
		log.Fatalf("Failed to subscribe to input topic: %v", err)
	}

	// Handle termination signals to gracefully exit
	signals := make(chan os.Signal, 1)
	signal.Notify(signals, syscall.SIGINT, syscall.SIGTERM)

	// Start consuming messages
	for {
		select {
		case sig := <-signals:
			log.Printf("Termination signal received: %v", sig)
			return
		default:
			msg, err := consumer.ReadMessage(-1)
			if err != nil {
				log.Printf("Consumer error: %v", err)
				continue
			}

			var inputMsg InputMessage
			err = json.Unmarshal(msg.Value, &inputMsg)
			if err != nil {
				log.Printf("Failed to parse JSON message: %v", err)
				continue
			}

			result := calculateLCM(inputMsg.Numbers)
			outputMsg := OutputMessage{
				Numbers: inputMsg.Numbers,
				LCM:     result,
			}

			outputJSON, err := json.Marshal(outputMsg)
			if err != nil {
				log.Printf("Failed to encode JSON message: %v", err)
				continue
			}

			// Produce the result to the output topic
			deliveryChan := make(chan kafka.Event, 10000)
			err = producer.Produce(&kafka.Message{
				TopicPartition: kafka.TopicPartition{Topic: &outputTopic, Partition: kafka.PartitionAny},
				Value:          outputJSON},
				deliveryChan)
			if err != nil {
				log.Printf("Failed to produce message: %v", err)
				continue
			}

			// Wait for the delivery report
			e := <-deliveryChan
			if m, ok := e.(*kafka.Message); ok {
				if m.TopicPartition.Error != nil {
					log.Printf("Failed to deliver message: %v", m.TopicPartition.Error)
				} else {
					log.Printf("Message delivered to topic %s [%d] at offset %v\n",
						*m.TopicPartition.Topic, m.TopicPartition.Partition, m.TopicPartition.Offset)
				}
			}

			// Save the input numbers and LCM to the Postgres table
			err = saveToPostgres(db, inputMsg.Numbers, result)
			if err != nil {
				log.Printf("Failed to save to Postgres: %v", err)
				continue
			}
		}
	}
}

func calculateLCM(numbers []int) int {
	lcm := numbers[0]
	for i := 1; i < len(numbers); i++ {
		lcm = calculateTwoLCM(lcm, numbers[i])
	}
	return lcm
}

func calculateTwoLCM(a, b int) int {
	return a * b / calculateGCD(a, b)
}

func calculateGCD(a, b int) int {
	for b != 0 {
		a, b = b, a%b
	}
	return a
}

func createTableIfNotExists(db *sql.DB) error {
	query := `
		CREATE TABLE IF NOT EXISTS lcm_results (
			numbers TEXT,
			stage TEXT,
			result TEXT
		);`
	_, err := db.Exec(query)
	return err
}

func saveToPostgres(db *sql.DB, numbers []int, result int) error {
	numbersJSON, err := json.Marshal(numbers)
	if err != nil {
		return fmt.Errorf("failed to marshal numbers to JSON: %v", err)
	}

	query := `
		INSERT INTO results (numbers, stage, result)
		VALUES ($1, 'stage3', $2);`
	_, err = db.Exec(query, numbersJSON, result)
	if err != nil {
		return fmt.Errorf("failed to save to Postgres: %v", err)
	}

	return nil
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
