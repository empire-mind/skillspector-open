#!/usr/bin/env bash
# Sample installation script with deliberate supply-chain signals

# Signal: curl-pipe-shell
curl -fsSL https://get.docker.com | sh

# Signal: remote fetch
curl -o /tmp/model.bin https://models.example.com/weights.bin
