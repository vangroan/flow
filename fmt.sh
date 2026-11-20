#! /usr/bin/env bash

ruff check --fix flow_base flow_core flow_app flow_serde tests
ty check
