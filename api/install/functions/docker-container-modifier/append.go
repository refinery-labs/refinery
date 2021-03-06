package main

import (
	"log"

	"github.com/google/go-containerregistry/pkg/crane"
	"github.com/google/go-containerregistry/pkg/logs"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/empty"
	"github.com/google/go-containerregistry/pkg/v1/mutate"
)

func ModifyDockerBaseImage(baseRef string, newTag string, appendLayers []v1.Layer, options ...crane.Option) (string, error) {
	var base v1.Image
	var err error

	if baseRef == "" {
		logs.Warn.Printf("base unspecified, using empty image")
		base = empty.Image
	} else {
		log.Printf("pulling %s", baseRef)
		base, err = crane.Pull(baseRef, options...)
		if err != nil {
			// Try again without auth
			base, err = crane.Pull(baseRef)
			if err != nil {
				return "", err
			}
		}
	}

	log.Printf("appending %v", appendLayers)
	img, err := mutate.AppendLayers(base, appendLayers...)
	if err != nil {
		return "", err
	}

	log.Printf("Getting config file %v", appendLayers)
	configFile, err := img.ConfigFile()
	if err != nil {
		return "", err
	}

	configFile.Config.Entrypoint = []string{"/var/runtime/bootstrap"}

	log.Printf("Getting config file...")
	img, err = mutate.ConfigFile(img, configFile)
	if err != nil {
		return "", err
	}

	log.Printf("Getting digest of image...")
	h, err := img.Digest()
	if err != nil {
		return "", err
	}

	log.Printf("pushing %v to %v", h.String(), newTag)
	if err := crane.Push(img, newTag, options...); err != nil {
		return "", err
	}
	return h.String(), nil
}
