import json

from system_prompt import SYSTEM

ROLE_NAMES = {"user": "buyer", "assistant": "seller"}

def build_messages(message, history, listing=None):
    lines = [f"{ROLE_NAMES[m['role']]}: {m['text']}" for m in history[-4:]]
    if listing:
        message = f"[Message sent from the Etsy listing: {listing}] {message}"
    latest =f"Latest buyer message:\n{message}"
    if lines:
        user = "Conversation so far:\n" + "\n".join(lines) + "\n\n" + latest
    else:
        user = latest
    return [{
        "role": "system", "content": SYSTEM
    }, {
        "role": "user", "content": user
    }]

def build_prompt(tok, message, history, listing=None):
    return tok.apply_chat_template(
        build_messages(message, history, listing),
        tokenize=False, add_generation_prompt=True,
        enable_thinking=False)

def build_answer(intent, subtype):
    return json.dumps({"intent": intent, "subtype": subtype},
                      ensure_ascii=False) + "<|im_end|>"

if __name__ == "__main__":
    with open("finetune_router/data/seed_train.jsonl", encoding="utf-8") as f:
        row = json.loads(f.readline())

    long_history = [{"role": "user" if i % 2 else "assistant", "text": f"h{i}"}
                    for i in range(1, 7)]
    cases = [
        ("带历史", row["message"], row["history"], None),
        ("无历史", "Can I change the shipping address on my order?", [], None),
        ("长历史", "latest question", long_history, None),
        ("带商品", "Received my journals and two pages are torn", [], "A6 Journal Set – Travel (#4580818745)"),
    ]
    for name, message, history, listing in cases:
        print(f"---- {name} ----")
        print(build_messages(message, history, listing)[1]["content"])