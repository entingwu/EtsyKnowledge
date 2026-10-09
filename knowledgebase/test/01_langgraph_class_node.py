from langgraph.graph import StateGraph

from knowledgebase.import_process.state import ImportGraphState


def a():
  pass

def b():
  pass

# 父类变成抽象类，抽象类必须要有一个抽象方法，而且所有子类必须实现父类的抽象方法。
from abc import ABC, abstractmethod
class Base(ABC):
    def __call__(self):
        self.process()

    @abstractmethod
    def process(self):
       pass

class A(Base):
    def process(self):
        pass

class B(Base):
    def process(self):
        pass


builder = StateGraph(state_schema=ImportGraphState)
builder.add_node(a)
builder.add_node(b)
builder.add_edge(a, b)

graph = builder.compile()
result = graph.invoke({})

# 后期这个函数谁调用的。

# 后期graph也要调用这个对象，它会把对象当函数去调用。
builder.add_node(A())
builder.add_node(B())

