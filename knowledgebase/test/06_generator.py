def func():
  print("aaa")
  yield 1
  print("bbb")
  yield 1

result = func()

print(next(result))
# print(next(result))