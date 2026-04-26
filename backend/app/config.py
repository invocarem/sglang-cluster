from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cassandra_hosts: str = "127.0.0.1"
    cassandra_port: int = 9042
    cassandra_datacenter: str = "datacenter1"
    cassandra_keyspace: str = "sglang_ui"
    scripts_dir: str = "/home/chenchen/sglang-cluster"
    api_host: str = "0.0.0.0"
    api_port: int = 18080
    master_node: str = "spark1"
    worker_node: str = "spark2"
    cx7_iface: str = "enp1s0f1np1"
    master_port: int = 29500
    server_port: int = 30000
    model_path: str = "/home/chenchen/huggingface/Qwen_Qwen3.5-2B"
    tp_size: int = 2

    model_config = SettingsConfigDict(env_prefix="SGLANG_UI_", extra="ignore")


settings = Settings()
