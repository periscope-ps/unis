#!/bin/bash

timeout 5 periscoped
[ $? -eq 124 ] || exit 1
