

base_endpoint_local = "http://127.0.0.1:{port}"
base_endpoint = "https://pd.{shard}.a.pvp.net"
base_endpoint_glz = "https://glz-{region}-1.{shard}.a.pvp.net"
base_endpoint_shared = "https://shared.{shard}.a.pvp.net"

regions = ["na","eu","latam","br","ap","kr","pbe"]
region_shard_override = {
    "latam":"na",
    "br":"na",
}
shard_region_override = {
    "pbe": "na"
}

queues = ["competitive", "custom", "deathmatch", "ggteam", "snowball", "spikerush", "unrated", "onefa", "null"]