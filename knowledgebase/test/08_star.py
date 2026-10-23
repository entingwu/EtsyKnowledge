dict1 = {
  'a': 1,
  'b': 2,
  'c': 3
}
dict2 = {**dict1}
print(dict2)

def fn(*args, **kwargs):
  print(args)
  print(kwargs)

fn('a', 'b', 'aa', 'bb', c='c', d='d')