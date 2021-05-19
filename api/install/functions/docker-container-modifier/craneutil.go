package main

import (
	"log"
	"os"
	"path"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ecr"
	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/google/go-containerregistry/pkg/crane"
	v1 "github.com/google/go-containerregistry/pkg/v1"
)

func loadCraneOptions() (options crane.Option, err error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-west-2"),
	})
	if err != nil {
		log.Println(err)
		return
	}

	ecrClient := ecr.New(sess)

	cfg, err := getAuthConfig(ecrClient)
	if err != nil {
		log.Println(err)
		return
	}

	authenticator := authn.FromConfig(cfg)

	options = crane.WithAuth(authenticator)
	return
}

func loadRuntimeLayers() (runtimeLayers []v1.Layer, err error) {
	refineryRuntimeRepo := os.Getenv("REFINERY_CONTAINER_RUNTIME_REPOSITORY")
	log.Println("Pulling Refinery container runtime from:", refineryRuntimeRepo)

	runtimeImage, err := crane.Pull(refineryRuntimeRepo)
	if err != nil {
		log.Println(err)
		return
	}

	log.Println("Getting runtime image layers...")
	return runtimeImage.Layers()
}

func loadRuntimeLayersFromTar() (runtimeLayers []v1.Layer, err error) {
	// TODO (cthompson) add some logic for checking for "updates"
	contentRoot := os.Getenv("LUNASEC_CONTENT_ROOT")
	runtimeContainerPath := path.Join(contentRoot, "refinery-container-runtime.tar")
	img, err := crane.Load(runtimeContainerPath)
	if err != nil {
		return
	}
	return img.Layers()
}
