def numgenerator(n):
  num = 1
  step = 1
  while num <= n:
    value = yield num
    print('value', value)
    if value:
      step = value
    num += step

num_generator = numgenerator(10)
print(num_generator.send(None))
print(num_generator.send(None))
print(num_generator.send(None))
print(num_generator.send(None))
print(num_generator.send(None))

print(num_generator.send(2))