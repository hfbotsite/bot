import time

import httpx


def main() -> None:
    base_url = "http://127.0.0.1:8010"

    payload = {
        "owner_id": "u_demo",
        "name": "smoke-bot",
        "runtime_version": "latest",
        "config": {"example": True},
    }

    r = httpx.post(
        f"{base_url}/api/v1/bots", json=payload, timeout=20, trust_env=False
    )
    r.raise_for_status()
    created = r.json()
    bot_id = created["bot_id"]
    print("created:", created)

    # poll status
    for _ in range(30):
        s = httpx.get(
            f"{base_url}/api/v1/bots/{bot_id}", timeout=10, trust_env=False
        ).json()
        print("status:", s)
        if s["status"] in ("running", "failed", "stopped"):
            break
        time.sleep(0.5)

    httpx.post(
        f"{base_url}/api/v1/bots/{bot_id}/stop", timeout=20, trust_env=False
    ).raise_for_status()
    s = httpx.get(
        f"{base_url}/api/v1/bots/{bot_id}", timeout=10, trust_env=False
    ).json()
    print("after stop:", s)

    httpx.post(
        f"{base_url}/api/v1/bots/{bot_id}/start", timeout=20, trust_env=False
    ).raise_for_status()
    s = httpx.get(
        f"{base_url}/api/v1/bots/{bot_id}", timeout=10, trust_env=False
    ).json()
    print("after start:", s)


if __name__ == "__main__":
    main()
