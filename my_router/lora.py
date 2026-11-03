import math
import torch
import torch.nn as nn

from transformers import AutoTokenizer, AutoModelForCausalLM

class LoRALinear(nn.Module):
    """
    W = W0 + (alpha / r) * B @ A
      W0：原始线性层权重，冻结
      A ∈ R^{r×in}：kaiming 初始化；B ∈ R^{out×r}：全 0 初始化 → 训练开始时 ΔW = 0，模型和原模型完全一样
    """
    def __init__(self, base: nn.Linear, r=8, alpha=16, dropout=0.05):
        super().__init__()
        self.base = base
        self.scaling = alpha / r
        dev, dt = base.weight.device, base.weight.dtype
        self.lora_A = nn.Parameter(torch.empty(r, base.in_features, device=dev, dtype=dt))
        self.lora_B = nn.Parameter(torch.zeros(base.out_features, r, device=dev, dtype=dt))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        dropout = self.dropout(x) # [2, 5, 1024]
        result = dropout @ self.lora_A.T # [2, 5, 8]
        result = result @ self.lora_B.T # [2, 5, 2048]
        return self.base(x) + result * self.scaling # [2, 5, 2048]

# 先冻结，再替换（正确）	冻结	可训练，因为是冻结之后才创建的	1,146,880
# 先替换，再冻结（错误, 错误顺序下，没有任何参数需要梯度，所以调用 loss.backward() 时 PyTorch 会直接报错.
def inject_lora(model, targets=("q_proj", "v_proj"), **kw):
    for p in model.parameters():
        p.requires_grad = False

    for name, module in list(model.named_modules()):
        parent_name, _, child_name = name.rpartition(".")
        if child_name in targets and isinstance(module, nn.Linear):
            parent = model.get_submodule(parent_name)
            # 1. 创建新模块
            wrapped = LoRALinear(module, **kw)
            # 2. 挂回父模块
            setattr(parent, child_name, wrapped)


def merge_lora(model):
    for name, module in list(model.named_modules()):
        if isinstance(module, LoRALinear):
            parent_name, _, child_name = name.rpartition(".")
            parent = model.get_submodule(parent_name)
            with torch.no_grad():
                # 1: add (B @ A) * scaling onto module.base.weight
                delta = module.lora_B @ module.lora_A * module.scaling # 算出旁路等价的权重增量 ΔW，形状是 [2048, 1024]
                module.base.weight += delta #  W_new = W + ΔW
            # 2: replace module with module.base
            setattr(parent, child_name, module.base)


def main():
    base = nn.Linear(1024, 2048, bias=False)
    lora = LoRALinear(base)
    x = torch.randn(2, 5, 1024) # [batch_size, seq_len, 1024]
    # [2, 5, 1024] → @ A.T → [2, 5, 8] → @ B.T → [2, 5, 2048]
    print("output shape:", lora(x).shape)
    print("same as base:", torch.equal(lora(x), base(x)))
    print("lora params:", sum(p.numel() for n, p in lora.named_parameters() if "lora_" in n))

    model_path = "/Users/entingwu/PycharmProjects/Finetune/model/Qwen3-0.6B"
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(model_path).float().eval()
    ids = tokenizer("Where is my order?", return_tensors="pt").input_ids

    # Test inject_lora
    original = test_inject_lora(model, ids)

    # Test merge_lora
    test_merge_lora(model, ids, original)

    # grad_check("A random, B zero:", zero_a=False)
    # grad_check("A zero, B zero:", zero_a=True)

def test_merge_lora(model, ids, original):
    for m in model.modules():
        if isinstance(m, LoRALinear):
            nn.init.normal_(m.lora_B, std=0.01)
    with torch.no_grad():
        with_lora = model(ids).logits
    print("LoRA changed logits by:", (with_lora - original).abs().max().item())

    merge_lora(model)
    with torch.no_grad():
        merged = model(ids).logits
    print("merge max diff:", (merged - with_lora).abs().max().item())
    print("LoRALinear left:", sum(isinstance(m, LoRALinear) for m in model.modules()))

def test_inject_lora(model, ids):
    with torch.no_grad():
        original = model(ids).logits

    inject_lora(model, r=8, alpha=16)
    model.eval()
    with torch.no_grad():
        lora_injected = model(ids).logits
    print("injected same as original:", torch.equal(lora_injected, original))

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel()for p in model.parameters())
    wrapped = sum(isinstance(m, LoRALinear) for m in model.modules())

    print("wrapped layers:", wrapped)
    print(f"trainable: {trainable:,} / {total:,} ({trainable / total:.2%})")
    return original

# B 初始化为 0，让旁路输出为 0，训练起点和预训练模型完全一致。A 用随机初始化，因为 B 的梯度依赖 A，如果 A 也是 0，两者梯度都是 0，训练就无法启动。
def grad_check(name, zero_a):
    lora = LoRALinear(nn.Linear(1024, 2048, bias=False))
    if zero_a:
        nn.init.zeros_(lora.lora_A)
    lora(torch.randn(2, 5, 1024)).pow(2).sum().backward()
    print(name, "A grad:", lora.lora_A.grad.abs().sum().item(),
          "B grad:", lora.lora_B.grad.abs().sum().item())

if __name__ == "__main__":
    main()
