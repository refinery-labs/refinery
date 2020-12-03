package main

import (
	"context"
	"io/ioutil"
	"log"
	"os"
	"path"

	"github.com/refinery-labs/refinery/golang/internal/worker"
	"github.com/refinery-labs/refinery/golang/pkg/dsl"
	"go.temporal.io/sdk/client"
	temporalWorker "go.temporal.io/sdk/worker"

	"go.uber.org/config"
)

func getConfigProvider(configDir string) config.Provider {
	files, err := ioutil.ReadDir(configDir)
	if err != nil {
		log.Fatalln(err)
	}

	var filenames []string
	for _, file := range files {
		filenames = append(filenames, path.Join(configDir, file.Name()))
	}

	provider, err := config.NewYAMLProviderWithExpand(os.LookupEnv, filenames...)
	if err != nil {
		log.Fatalln(err)
	}
	return provider
}

func main() {
	provider := getConfigProvider("./config/workflow-manager-worker")

	var workerConfig worker.WorkerConfig
	if err := provider.Get("workflow-manager-worker").Populate(&workerConfig); err != nil {
		log.Fatalln(err)
	}

	// The client and worker are heavyweight objects that should be created once per process.
	c, err := client.NewClient(client.Options{
		HostPort:  workerConfig.TemporalHostPort,
		Namespace: "refinery",
	})
	if err != nil {
		log.Fatalln("Unable to create client", err)
	}
	defer c.Close()

	clientManager := worker.NewAwsClientManager(
		workerConfig,
	)

	w := temporalWorker.New(c, "dsl", temporalWorker.Options{
		BackgroundActivityContext: context.Background(),
	})

	w.RegisterWorkflow(dsl.SimpleDSLWorkflow)
	w.RegisterActivity(&worker.RefineryAwsActivities{
		clientManager,
	})

	err = w.Run(temporalWorker.InterruptCh())
	if err != nil {
		log.Fatalln("Unable to start worker", err)
	}
}
