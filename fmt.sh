#! /usr/bin/env bash

ruff check --fix flow_base flow_core tests
ty check
