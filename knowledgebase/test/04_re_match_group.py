import re

stripped_line = "````123~~~abc``````"

code_block_marker_match = re.match(r'^(`{3,}|~{3,}).*?(`{3,}|~{3,}).*?(`{3,}|~{3,})$', stripped_line)
if code_block_marker_match:
  print('0', code_block_marker_match.group(0))
  marker1 = code_block_marker_match.group(1)
  marker2 = code_block_marker_match.group(2)
  marker3 = code_block_marker_match.group(3)
  print("\n")
  print(marker1)
  print(marker2)
  print(marker3)

code_block_marker = re.compile(r'^(`{3,}|~{3,}).*?(`{3,}|~{3,}).*?(`{3,}|~{3,})$')
code_block_marker_match = code_block_marker.match(stripped_line)
if code_block_marker_match:
  print('0', code_block_marker_match.group(0))
  marker1 = code_block_marker_match.group(1)
  marker2 = code_block_marker_match.group(2)
  marker3 = code_block_marker_match.group(3)
  print("\n")
  print(marker1)
  print(marker2)
  print(marker3)