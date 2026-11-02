import json
import torch
from transformers import AutoTokenizer
from prompt import build_prompt, build_answer

def encode(tokenizer, prompt, answer, max_length=1024):
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    answer_ids = tokenizer(answer, add_special_tokens=False)["input_ids"]
    assert len(prompt_ids) + len(answer_ids) <= max_length, "Sample too long: keep fewer history messages in the prompt instead of truncating here"
    ids = prompt_ids + answer_ids
    mask = [0] * len(prompt_ids) + [1] * len(answer_ids)
    return ids, mask

def collate(batch, pad_id):
    pass

if __name__ == "__main__":
    tokenizer = AutoTokenizer.from_pretrained("/Users/entingwu/PycharmProjects/Finetune/model/Qwen3-0.6B")

    with open("finetune_router/data/seed_train.jsonl", encoding="utf-8") as f:
      rows = [json.loads(f.readline()) for _ in range(3)]

    batch = []
    for row in rows:
      intent, _, subtype = row["label"].partition(":")
      prompt = build_prompt(tokenizer, row["message"], row["history"])
      answer = build_answer(intent, subtype)
      batch.append(encode(tokenizer, prompt, answer))

    # encode
    # ids, mask = encode(tokenizer, prompt, answer)
    # answer_ids = [i for i, m in zip(ids, mask) if m == 1]
    # print("total length:", len(ids), "mask=1 count:", sum(mask))
    # print("answer tokens:", repr(tokenizer.decode(answer_ids)))

    # collate
    input_ids, labels, loss_mask = collate(batch, tokenizer.pad_token_id)
    print("shapes:", input_ids.shape, labels.shape, loss_mask.shape)
    for i in range(3):
      print(repr(tokenizer.decode(labels[i][loss_mask[i] == 1])))