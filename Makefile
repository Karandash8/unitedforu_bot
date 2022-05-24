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

# build uniedforu-bot images for all platforms
# after build, an image for the last specified platform will be tagged with IMAGE_TAG locally
build_and_push_multiplatform : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
build_and_push_multiplatform :
	@echo "Building unitedforu-bot images (linux/amd64, linux/arm64)"
	@docker buildx build --platform linux/arm64,linux/amd64 --tag $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG) -f $(DOCKERFILE) --push .
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

# run a container from unitedforu-bot image
run : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
run :
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make stop ; \
	fi
	@echo "Starting unitedforu-bot container"
	@docker run -itd \
	-e TELEGRAM_API_TOKEN=$(TELEGRAM_API_TOKEN) \
	-e TELEGRAM_LIST_OF_ADMIN_IDS=$(TELEGRAM_LIST_OF_ADMIN_IDS) \
	-e STORE_SHEET_ID=$(STORE_SHEET_ID) \
	-e LOAD_SHEET_ID=$(LOAD_SHEET_ID) \
	-e SHEET_CREDENTIALS_PATH=$(SHEET_CREDENTIALS_PATH) \
	-v `pwd`/.service_account.json:/root/.service_account.json \
	--name $(CONTAINER_NAME) $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Done"

# stop unitedforu-bot container
stop :
	@echo "Stopping and removing unitedforu-bot container"
	@docker container rm -f $(CONTAINER_NAME)
	@echo "Done"

# run a container from unitedforu-bot image and mount local bot folder.
# This helps to avoid rebuilding the image on every change.
debug : CONTAINER_STATUS := `docker container ls -a | grep $(CONTAINER_NAME)`
debug :
	@if [ -n "$(CONTAINER_STATUS)" ] ; then \
		make stop ; \
	fi
	@echo "Starting unitedforu-bot container in debug mode"
	@docker run -itd \
	-e TELEGRAM_API_TOKEN=$(TELEGRAM_API_TOKEN) \
	-e TELEGRAM_LIST_OF_ADMIN_IDS=$(TELEGRAM_LIST_OF_ADMIN_IDS) \
	-e STORE_SHEET_ID=$(STORE_SHEET_ID) \
	-e LOAD_SHEET_ID=$(LOAD_SHEET_ID) \
	-e SHEET_CREDENTIALS_PATH=$(SHEET_CREDENTIALS_PATH) \
	-v `pwd`/.service_account.json:/root/.service_account.json \
	-v `pwd`/bot-unitedforu:/bot-unitedforu \
	--name $(CONTAINER_NAME) $(DOCKERHUB_ACCOUNT)/$(IMAGE_NAME):$(IMAGE_TAG)
	@echo "Done"