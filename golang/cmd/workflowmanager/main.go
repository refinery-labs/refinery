package main

import (
	"io/ioutil"
	"log"
	"os"
	"path"

	"go.uber.org/config"

	"github.com/gofiber/fiber/v2"
	"github.com/refinery-labs/refinery/golang/internal/workflowmanager"
	"go.temporal.io/sdk/client"
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
	provider := getConfigProvider("./config")

	var workflowManagerConfig workflowmanager.WorkflowManagerConfig
	if err := provider.Get("workflow-manager").Populate(&workflowManagerConfig); err != nil {
		log.Fatalln(err)
	}

	// The client is a heavyweight object that should be created once per process.
	temporalClient, err := client.NewClient(client.Options{
		HostPort:  workflowManagerConfig.TemporalHostPort,
		Namespace: "refinery",
	})
	if err != nil {
		log.Fatalln("Unable to create client", err)
	}

	workflowStore := workflowmanager.NewPostgresqlWorkflowStore(workflowManagerConfig.DatabaseURI)

	workflowManager := workflowmanager.NewTemporalWorkflowManager(temporalClient, workflowStore)

	controller := &workflowmanager.Controller{
		WorkflowManager: workflowManager,
		TemporalClient:  temporalClient,
	}

	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
		ErrorHandler:          controller.ErrorHandler,
	})

	api := app.Group("/api")
	v1 := api.Group("/v1")

	v1.All("/deployment/:deploymentID/workflow/:workflowID", controller.StartWorkflow)

	v1.Get("/deployment/:deploymentID", func(c *fiber.Ctx) error { return nil })
	v1.Delete("/deployment/:deploymentID", controller.CancelWorkflowsForDeployment)
	v1.Post("/deployment", controller.CreateWorkflowsForDeployment)
	v1.Delete("/executions", controller.StopAllOpenWorkflows)

	app.Listen(":3000")
}
