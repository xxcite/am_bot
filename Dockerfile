# Stage 1: Build stage
FROM python:3-slim AS builder

WORKDIR /usr/src/app

# Install dependencies needed for Rust and Cargo
RUN apt-get update && apt-get install -y curl build-essential

# Install Rust and Cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    echo 'export PATH="/root/.cargo/bin:$PATH"' >> /root/.bashrc && \
    /root/.cargo/bin/rustup default stable

# Ensure Rust and Cargo are available during build
ENV PATH="/root/.cargo/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3-slim

WORKDIR /usr/src/app

# Copy only the necessary files from the builder
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH="/root/.local/bin:$PATH"

CMD ["python", "./watch_script.py"]
