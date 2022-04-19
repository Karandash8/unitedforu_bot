DOCKERFILE := unitedforu-bot.Dockerfile
IMAGE_NAME := unitedforu-bot
IMAGE_TAG := latest
CONTAINER_NAME := unitedforu-bot
DOCKERHUB_ACCOUNT := karandash8

default :
	@echo "ERROR: Please specify the target"

# build uniedforu-bot image
build : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
build :
	@echo "Building unitedforu-bot image"
	@docker build --tag $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG) -f $(DOCKERFILE) .
	@echo "Done"
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make run ; \
	fi

# delete local uniedforu-bot image
clean : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
clean :
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make stop ; \
	fi
	@echo "Deleting unitedforu-bot image"
	@docker image rm $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Done"

# push uniedforu-bot image o the registry
push :
	@echo "Pushing unitedforu-bot image to the registry"
	docker push $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Done"

# run a container from unitedforu-bot image
run : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
run :
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make stop ; \
	fi
	@echo "Starting unitedforu-bot container"
	@docker run -itd -e API_TOKEN=$(API_TOKEN) --name $(CONTAINER_NAME) $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Done"

# stop unitedforu-bot container
stop :
	@echo "Stopping and removing unitedforu-bot container"
	@docker container rm -f $(CONTAINER_NAME)
	@echo "Done"