def fn():
  a = 100
  def fn2():
    nonlocal a
    a += 1
    print(a)
  return fn2

print(fn.__closure__)
f = fn()
f()
print(f.__closure__)
f()

f1 = fn()
f1()
print(f1.__closure__)
f1()
print(f1.__closure__)

f = None
f1 = None