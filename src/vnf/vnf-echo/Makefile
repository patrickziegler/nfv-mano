TAG=vnf-echo

all:
	docker build -t ${TAG} .

run:
	docker run -it --rm ${TAG}

clean:
	docker rmi ${TAG}
