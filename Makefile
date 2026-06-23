.PHONY: install install-all build swift hotkey whisper clean test

install:
	pip install -e .

install-dev:
	pip install -e ".[openai,voice,menubar]"

install-all:
	pip install -e ".[openai,voice,menubar]"

build:
	python -m build

swift:
	cd swift && swiftc -O -o ax_inspector ax_inspector.swift -framework Cocoa -framework ApplicationServices
	cd swift && swiftc -O -o screen_ocr screen_ocr.swift -framework Cocoa -framework Vision
	@echo "✅ Swift 工具编译完成"

menubar:
	cd swift && swiftc -O -o menubar menubar.swift -framework Cocoa -framework Foundation
	mkdir -p ~/.knowagent/bin && cp swift/menubar ~/.knowagent/bin/
	@echo "✅ 菜单栏应用编译完成"
	@echo "   运行: bash scripts/menubar.sh start"

hotkey:
	cd swift && swiftc -O -o hotkey hotkey.swift -framework Cocoa -framework Carbon
	@echo "✅ 全局快捷键编译完成"

whisper:
	@echo "📥 下载 whisper.cpp..."
	@if [ ! -d /tmp/whisper.cpp ]; then git clone --depth 1 https://github.com/ggerganov/whisper.cpp /tmp/whisper.cpp; fi
	cd /tmp/whisper.cpp && make -j 2>/dev/null || make
	/tmp/whisper.cpp/models/download-ggml-model.sh base
	mkdir -p ~/.knowagent/bin
	cp /tmp/whisper.cpp/build/bin/whisper ~/.knowagent/bin/ 2>/dev/null || \
	cp /tmp/whisper.cpp/whisper ~/.knowagent/bin/ 2>/dev/null || true
	@echo "✅ whisper.cpp 编译完成"

clean:
	rm -rf dist/ build/ *.egg-info/
	rm -rf swift/ax_inspector swift/screen_ocr swift/hotkey
	rm -rf ~/.knowagent/bin/
	@echo "✅ 清理完成"

test:
	python -m pytest tests/ -v
