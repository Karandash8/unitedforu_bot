DOCKERFILE := unitedforu-bot.Dockerfile
IMAGE_TAG := unitedforu-bot
CONTAINER_NAME := unitedforu-bot

default :
	@echo "ERROR: Please specify the target"

build : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
build :
	@echo "Building unitedforu-bot image"
	@docker build --tag $(IMAGE_TAG) -f $(DOCKERFILE) .
	@echo "Done"
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make run ; \
	fi

clean : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
clean :
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make remove ; \
	fi
	@echo "Deleting unitedforu-bot image"
	@docker image rm $(IMAGE_TAG)
	@echo "Done"

push :
	@echo "Pushing unitedforu-bot image to the registry"
	# TBD
	@echo "Done"

run : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
run :
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make remove ; \
	fi
	@echo "Starting unitedforu-bot container"
	@docker run -itd -e API_TOKEN=$(API_TOKEN) --name $(CONTAINER_NAME) $(IMAGE_TAG)
	@echo "Done"

remove :
	@echo "Removing unitedforu-bot container"
	@docker container rm -f $(IMAGE_TAG)
	@echo "Done"