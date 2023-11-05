group "default" {
  targets = ["dapp", "server", "console"]
}

# crossenv toolchain for python dapps
target "toolchain-python" {
  context = "./docker-riscv"
  target  = "toolchain-python"
  tags    = ["cartesi/toolchain-python"]
}

target "local-deployments" {
  context = "./docker-riscv"
  target = "local-deployments-stage"
}

target "deployments" {
  context = "./docker-riscv"
  target = "deployments-stage"
}

target "wrapped" {
  context = "./docker-riscv"
  target = "wrapped-stage"
  contexts = {
    dapp = "target:dapp"
  }
}

target "fs" {
  context = "./docker-riscv"
  target  = "fs-stage"
  contexts = {
    wrapped = "target:wrapped"
    deployments = "target:deployments"
    local-deployments = "target:local-deployments"
  }
}

target "server" {
  context = "./docker-riscv"
  target  = "server-stage"
  contexts = {
    fs = "target:fs"
  }
}

target "console" {
  context = "./docker-riscv"
  target  = "console-stage"
  contexts = {
    fs = "target:fs"
  }
}

target "machine" {
  context = "./docker-riscv"
  target  = "machine-stage"
  contexts = {
    fs = "target:fs"
  }
}