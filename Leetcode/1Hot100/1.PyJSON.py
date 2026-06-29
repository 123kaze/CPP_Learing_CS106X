import json

text = '''
{
  "user": {
    "name": "Tom",
    "age": 18
  }
}
'''
def pretty_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)

def compact_json(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))

def parse_path(path: str):
    tokens = []
    i = 0
    n = len(path)
    if path.startswith("$"):
        i = 1
        if i<n and path[i]=='.':
            i+=1
    
    while i<n:
        if path[i] == '.':
            i+=1
            continue
        
        if path[i] == "[":
            j = path.find("]",i)
            if j == -1:
                raise ValueError('Format Error: Lost ]')
            content = path[i+1:j].strip()

            if not content.isdigit():
                raise ValueError("Fromat Error: index must be digits")
            tokens.append(("index",int(content)))
            i = j+1
        
        else:
            start = i

            while i<n and path[i] not in ".[":
                i+=1
            
            field_name = path[start:i]
            if not field_name:
                raise ValueError("Format Error: None key name")
            tokens.append(('field',field_name))
        
    return tokens

def get_value(data, path):
    tokens = parse_path(path)
    cur = data

    for kind, value in tokens:
        if kind == "field":
            if not isinstance(cur, dict):
                raise TypeError(f"当前节点不是对象，不能访问字段 {value}")

            if value not in cur:
                raise KeyError(f"字段不存在：{value}")

            cur = cur[value]

        elif kind == "index":
            if not isinstance(cur, list):
                raise TypeError(f"当前节点不是数组，不能访问下标 {value}")

            if value < 0 or value >= len(cur):
                raise IndexError(f"数组下标越界：{value}")

            cur = cur[value]

    return cur

try:
    data = json.loads(text)
    print(data)
    print(compact_json(data))
    print(pretty_json(data))
    print(parse_path("user.name"))
    print(parse_path("orders[0].price"))
    print(parse_path("$.orders[1].id"))
except json.JSONDecodeError as e:
    print("JSON 不合法")
    print("错误信息:", e.msg)
    print("错误行:", e.lineno)
    print("错误列:", e.colno)