package main

import (
	"log"
	"strings"

	"github.com/google/go-containerregistry/pkg/crane"
	"github.com/google/go-containerregistry/pkg/logs"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/empty"
	"github.com/google/go-containerregistry/pkg/v1/mutate"
)

type ContainerConfig struct {
	tag          string
	deploymentID string
	workDir      string
}

type DockerContainerModifier interface {
	LoadImage() (base v1.Image, err error)
	AppendLayersToBaseImage(base v1.Image, appendLayers []v1.Layer) (img v1.Image, containerConfig ContainerConfig, err error)
	SaveImageToFile(img v1.Image, newTag, filename string) (err error)
	PushImage(img v1.Image, newTag string) (err error)
}

type dockerContainerModifier struct {
	localDev         bool
	baseRef          string
	modifyEntrypoint bool
	options          []crane.Option
}

func NewDockerContainerModifier(
	baseRef string,
	localDev bool,
	modifyEntrypoint bool,
	options ...crane.Option,
) DockerContainerModifier {
	return &dockerContainerModifier{
		baseRef:          baseRef,
		localDev:         localDev,
		modifyEntrypoint: modifyEntrypoint,
		options:          options,
	}
}

func (d *dockerContainerModifier) LoadImage() (base v1.Image, err error) {
	if d.localDev {
		return crane.Load(d.baseRef)
	} else {
		return d.pullBaseImage(d.baseRef)
	}
}

func (d *dockerContainerModifier) AppendLayersToBaseImage(base v1.Image, appendLayers []v1.Layer) (img v1.Image, containerConfig ContainerConfig, err error) {
	log.Printf("appending %v layers to %s", len(appendLayers), d.baseRef)
	img, err = mutate.AppendLayers(base, appendLayers...)
	if err != nil {
		log.Println(err)
		return
	}

	configFile, err := img.ConfigFile()
	if err != nil {
		log.Println(err)
		return
	}

	if d.modifyEntrypoint {
		img, err = modifyImageEntrypoint(img, configFile)
		if err != nil {
			log.Println(err)
			return
		}
	}

	log.Printf("getting digest of image...")
	imageHash, err := img.Digest()
	if err != nil {
		log.Println(err)
		return
	}
	log.Printf("created new image with hash: %v", imageHash.String())
	containerConfig = getContainerConfigFromImage(configFile, imageHash)
	return
}

func (d *dockerContainerModifier) SaveImageToFile(img v1.Image, newTag, filename string) (err error) {
	return crane.Save(img, newTag, filename)
}

func (d *dockerContainerModifier) PushImage(img v1.Image, newTag string) (err error) {
	return crane.Push(img, newTag, d.options...)
}

func (d *dockerContainerModifier) pullBaseImage(baseRef string) (base v1.Image, err error) {
	if baseRef == "" {
		logs.Warn.Printf("base unspecified, using empty image")
		base = empty.Image
		return
	}

	log.Printf("pulling %s", baseRef)
	base, err = crane.Pull(baseRef, d.options...)
	// If we succeeded, then return...
	if err == nil {
		return
	}
	// ...otherwise try again without auth
	return crane.Pull(baseRef)
}

func getContainerConfigFromImage(configFile *v1.ConfigFile, imageHash v1.Hash) (containerConfig ContainerConfig) {
	containerConfig.workDir = configFile.Config.WorkingDir

	for _, envVar := range configFile.Config.Env {
		if strings.Index(envVar, "REFINERY_DEPLOYMENT_ID") == 0 {
			parts := strings.Split(envVar, "=")
			containerConfig.deploymentID = parts[len(parts)-1]
		}
	}

	containerConfig.tag = imageHash.String()
	return
}

func modifyImageEntrypoint(img v1.Image, configFile *v1.ConfigFile) (newImg v1.Image, err error) {
	configFile.Config.Entrypoint = []string{"/var/runtime/bootstrap"}
	return mutate.ConfigFile(img, configFile)
}
