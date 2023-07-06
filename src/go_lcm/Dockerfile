# Build stage
FROM golang:1.19 AS builder

WORKDIR /build

# Copy the Go module files and download dependencies
COPY go.mod go.sum ./
RUN go mod download -x -json

# Copy the source code
COPY *.go ./

# Build the Go application
RUN CGO_ENABLED=0 GOOS=linux go build -o lcm

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy the built binary from the previous stage
COPY --from=builder /build/lcm /app/lcm

# Run the Go application
CMD ["/app/lcm"]
