# ベースイメージとしてPython 3.11 (Slim版) を使用
FROM python:3.11-slim

# Proxy settings
ARG http_proxy
ARG https_proxy
ARG no_proxy
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

ENV http_proxy=${http_proxy} \
    https_proxy=${https_proxy} \
    no_proxy=${no_proxy} \
    HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY}

# 環境変数の設定
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64" \
    PATH="$JAVA_HOME/bin:$PATH"

# システムパッケージのインストール (OpenJDK 17など)
# mkdir -p /usr/share/man/man1 はOpenJDKインストールの既知の問題回避用
RUN apt-get update && \
    mkdir -p /usr/share/man/man1 && \
    apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# Alloyの配置 (ホストの alloy ディレクトリをコピー)
# これにより /app/alloy/app/org.alloytools.alloy.dist.jar 等にアクセス可能になる
COPY alloy /app/alloy

# Python依存関係のインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードのコピー
# .dockerignore で不要なファイルを除外することを推奨
COPY . .

# コンテナ起動時のデフォルトコマンド
# 開発用なので bash をデフォルトにしておくか、アプリ起動コマンドにする
CMD ["/bin/bash"]
