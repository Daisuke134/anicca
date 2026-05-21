BINARY_NAME=greenlight
VERSION?=$(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
LDFLAGS=-ldflags "-X main.version=$(VERSION)"

.PHONY: build clean test lint install

build:
	go build $(LDFLAGS) -o build/$(BINARY_NAME) ./cmd/greenlight

install:
	go install $(LDFLAGS) ./cmd/greenlight

clean:
	rm -rf build/

test:
	go test ./... -v

lint:
	golangci-lint run ./...

# Cross-compile for release
release:
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o build/$(BINARY_NAME)-darwin-arm64 ./cmd/greenlight
	GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o build/$(BINARY_NAME)-darwin-amd64 ./cmd/greenlight
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o build/$(BINARY_NAME)-linux-amd64 ./cmd/greenlight

deps:
	go mod tidy
	go mod download
