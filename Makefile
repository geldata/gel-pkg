.PHONY: build test test-systemd test-published update-images check-target


SUPPORTED_TARGETS = \
	debian-buster \
	debian-bullseye \
	debian-bookworm \
	ubuntu-bionic \
	ubuntu-focal \
	ubuntu-jammy \
	ubuntu-noble \
	ubuntu-oracular \
	centos-7 \
	centos-8 \
	rockylinux-9 \
	amazonlinux-2023 \
	fedora-40 \
	linux-x86_64 \
	linuxmusl-x86_64 \
	linux-aarch64 \
	linuxmusl-aarch64

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PLATFORM = $(firstword $(subst -, ,$(TARGET)))
ARCH ?= $(shell uname -m)
DISTRO = $(lastword $(subst -, ,$(TARGET)))
OUTPUTDIR := /tmp/artifacts
GET_SHELL :=
SSH_KEY :=
PACKAGE_SERVER :=
PKG_TEST_JOBS :=

EXTRAENV =
EXTRAVOLUMES =

DOCKER_ARCH__x86_64 = amd64
DOCKER_ARCH__aarch64 = arm64v8
DOCKER_ARCH__arm64 = arm64v8
DOCKER_ARCH = $(DOCKER_ARCH__$(ARCH))
ifeq ($(DOCKER_ARCH),)
	DOCKER_ARCH=$(ARCH)
endif
DOCKER_ARCH_PREFIX=$(DOCKER_ARCH)/
DOCKER_PLATFORM__arm64v8 = linux/arm64/v8
DOCKER_PLATFORM= $(DOCKER_PLATFORM__$(DOCKER_ARCH))
ifeq ($(DOCKER_PLATFORM),)
	DOCKER_PLATFORM=linux/$(DOCKER_ARCH)
endif

ifeq ($(METAPKGDEV),true)
	_METAPKG_PATH = $(shell python -c 'import metapkg;print(metapkg.__path__[0])')
	EXTRAVOLUMES += -v $(_METAPKG_PATH):/metapkg
	EXTRAENV += -e METAPKG_PATH=/metapkg
endif

ifeq ($(GET_SHELL),true)
	COMMAND = bash
	EXTRAENV += -e GET_SHELL="$(GET_SHELL)"
endif

ifneq ($(SRC_REF),)
	EXTRAENV += -e SRC_REF="$(SRC_REF)"
endif

ifneq ($(PKG_VERSION_SLOT),)
	EXTRAENV += -e PKG_VERSION_SLOT="$(PKG_VERSION_SLOT)"
endif

ifneq ($(PKG_REVISION),)
	EXTRAENV += -e PKG_REVISION="$(PKG_REVISION)"
endif

ifneq ($(PKG_SUBDIST),)
	EXTRAENV += -e PKG_SUBDIST="$(PKG_SUBDIST)"
endif

ifneq ($(PKG_TAGS),)
	EXTRAENV += -e PKG_TAGS="$(PKG_TAGS)"
endif

ifneq ($(PKG_INSTALL_REF),)
	EXTRAENV += -e PKG_INSTALL_REF="$(PKG_INSTALL_REF)"
endif

ifneq ($(PKG_COMPRESSION),)
	EXTRAENV += -e PKG_COMPRESSION="$(PKG_COMPRESSION)"
endif

ifneq ($(EXTRA_OPTIMIZATIONS),)
	EXTRAENV += -e EXTRA_OPTIMIZATIONS=true
endif

ifneq ($(DEBUG_SYMBOLS),)
	EXTRAENV += -e DEBUG_SYMBOLS=true
endif

ifneq ($(PACKAGE),)
    EXTRAENV += -e PACKAGE="$(PACKAGE)"
endif

ifneq ($(PKG_PLATFORM_LIBC),)
	EXTRAENV += -e PKG_PLATFORM_LIBC="$(PKG_PLATFORM_LIBC)"
endif

ifneq ($(PKG_PLATFORM_ARCH),)
	EXTRAENV += -e PKG_PLATFORM_ARCH="$(PKG_PLATFORM_ARCH)"
endif

ifneq ($(BUILD_GENERIC),)
	EXTRAENV += -e BUILD_GENERIC="$(BUILD_GENERIC)"
endif

ifneq ($(PKG_BUILD_JOBS),)
	EXTRAENV += -e PKG_BUILD_JOBS="$(PKG_BUILD_JOBS)"
endif

ifeq ($(BUILD_IS_RELEASE),true)
	EXTRAENV += -e BUILD_IS_RELEASE=true
endif

check-target:
ifeq ($(TARGET),)
	$(error "Please specify the TARGET variable.")
endif

ifeq ($(filter $(TARGET),$(SUPPORTED_TARGETS)),)
	$(error Unsupported target: $(TARGET),  \
			supported targets are: $(SUPPORTED_TARGETS))
endif

build: check-target
	make -C integration/linux/build
	env BUILDKIT_PROGRESS=plain \
		docker build -t $(DOCKER_ARCH_PREFIX)edgedb-pkg/build:$(TARGET) \
		--build-arg DOCKER_ARCH=$(DOCKER_ARCH_PREFIX) \
		--platform $(DOCKER_PLATFORM) \
		integration/linux/build/$(TARGET)
	docker run -it --rm \
		-v $(ROOT):/src \
		-v /tmp/pkgcache:/root/.cache/ \
		-v $(OUTPUTDIR):/src/artifacts \
		$(EXTRAVOLUMES) \
		$(EXTRAENV) \
		-e PKG_PLATFORM=$(PLATFORM) \
		-e PKG_PLATFORM_VERSION=$(DISTRO) \
		-e PYTHONPATH=/src \
		-w /src \
		--platform $(DOCKER_PLATFORM) \
		$(DOCKER_ARCH_PREFIX)edgedb-pkg/build:$(TARGET) \
		$(COMMAND)

test: check-target
	make -C integration/linux/test
	env BUILDKIT_PROGRESS=plain \
		docker build -t $(DOCKER_ARCH_PREFIX)edgedb-pkg/test:$(TARGET) \
		--build-arg DOCKER_ARCH=$(DOCKER_ARCH_PREFIX) \
		--platform $(DOCKER_PLATFORM) \
		integration/linux/test/$(TARGET)
	docker run -it --rm \
		-v $(ROOT):/src \
		-v $(OUTPUTDIR):/artifacts \
		$(EXTRAENV) \
		-e PKG_PLATFORM=$(PLATFORM) \
		-e PKG_PLATFORM_VERSION=$(DISTRO) \
		-e PKG_TEST_JOBS=$(PKG_TEST_JOBS) \
		--platform $(DOCKER_PLATFORM) \
		$(DOCKER_ARCH_PREFIX)edgedb-pkg/test:$(TARGET) \
		$(COMMAND)

test-systemd: check-target
	make -C integration/linux/test-systemd
	env BUILDKIT_PROGRESS=plain \
		docker build -t edgedb-pkg/test-systemd:$(TARGET) integration/linux/test-systemd/$(TARGET)
	podman run -it --rm \
		--cap-add SYS_ADMIN \
		--cgroupns=host \
		--cgroup-parent="containers.slice" \
		--systemd true \
		-v $(ROOT):/src \
		-v $(OUTPUTDIR):/artifacts \
		$(EXTRAENV) \
		-e PKG_PLATFORM=$(PLATFORM) \
		-e PKG_PLATFORM_VERSION=$(DISTRO) \
		docker-daemon:edgedb-pkg/test-systemd:$(TARGET)

publish:
	make -C integration/linux/upload
	env BUILDKIT_PROGRESS=plain \
		docker build -t edgedb-pkg/upload:linux-x86_64 integration/linux/upload/linux-x86_64
	docker run -it --rm \
		$(EXTRAENV) \
		-e PKG_PLATFORM=$(PLATFORM) \
		-e PKG_PLATFORM_VERSION=$(DISTRO) \
		-e PACKAGE_UPLOAD_SSH_KEY_FILE="/sshkey" \
		-e PACKAGE_SERVER=$(PACKAGE_SERVER) \
		-v $(SSH_KEY):/sshkey \
		-v $(OUTPUTDIR):/artifacts \
		edgedb-pkg/upload:linux-x86_64 \
		$(COMMAND)

test-published: check-target
	make -C integration/linux/testpublished
	export BUILDKIT_PROGRESS=plain
	docker build -t edgedb-pkg/testpublished:$(TARGET) integration/linux/testpublished/$(TARGET)
	docker run -it --rm \
		$(EXTRAENV) \
		-e PKG_PLATFORM=$(PLATFORM) \
		-e PKG_PLATFORM_VERSION=$(DISTRO) \
		-e PKG_NAME=$(PKG_NAME) \
		-v $(ROOT):/src \
		edgedb-pkg/testpublished:$(TARGET) \
		$(COMMAND)
