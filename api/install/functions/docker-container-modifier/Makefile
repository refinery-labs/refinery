.PHONY: build clean deploy

build:
	env CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o bin/main main.go append.go

clean:
	rm -rf ./bin

package: clean build
	zip docker-container-modifier.zip ./bin/main
