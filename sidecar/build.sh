#!/bin/sh
# Clone and build whisper.cpp whisper-server with Metal acceleration (Apple Silicon).
set -eu
cd "$(dirname "$0")"

if [ ! -d whisper.cpp ]; then
    git clone https://github.com/ggml-org/whisper.cpp
fi

cd whisper.cpp
cmake -B build -DGGML_METAL=ON
cmake --build build --target whisper-server -j

echo "Built: $(pwd)/build/bin/whisper-server"
echo "Next: fetch a model, e.g. from the repo root:"
echo "  cd whisper.cpp/models && sh download-ggml-model.sh base-q5_1"
