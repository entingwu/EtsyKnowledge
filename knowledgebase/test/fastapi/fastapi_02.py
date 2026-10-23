#路径参数是前端在发请求的时候把参数写在路径的后面， http://www.baidu.com/index/1/yangmi
#上面的案例1和yangmi就是路径参数
#请求方式 一般我们关注4种：get post put delete
#get和delete请求一般没有请求体
#post和put请求一般有请求体
#前端在发送请求的时候，请求又分成两大类：1普通请求  2ajax请求
#普通请求一般只有get和post请求  浏览器地址栏输入回车get   点击页面的链接a标签get  表单提交post
#ajax请求 就是通过js代码发起的请求  一般4种都有，现在我们前端基本发的都是ajax请求
#普通请求发送请求的时候浏览器页面会刷新页面，ajax请求不会



import uvicorn
from fastapi import FastAPI, Path, Query, Body

app = FastAPI()

# todo 一、接收路径参数
@app.get("/testpath/{id}/{name}")
#路径参数占位，路径参数是属于路径的一部分
#后期fastapi拿到前端的路径后要做对比匹配，参数也得参与

#任何参数考虑三个点
#1、前端怎么传
#2、后端怎么接
#3、后端怎么校验

#一旦传递路径参数，那么前后都必须传，不能可传可不传，否则就不是参数了
#参数一般都要做校验


def testpath(
    id: int=Path(..., description="用户id", gt=0, le=100),
    name: str=Path(..., description="用户名称", min_length=2)
):
    return {"id":id, "name":name}


# todo 二、接收查询参数
#1、前端怎么传   在url路径后面以？分割，k=v&k=v的形式传递,例如：http://www.baidu.com/index?id=1&name=yangmi，查询参数不占用路径的位置
#2、后端怎么接   直接在形参当中写即可 形参名字要和前端传递的k一致
#3、后端怎么校验 Query(...)  default和三点是互斥的，二者只能选其一
@app.get("/testquery")
def testquery(
        # id: int,#没有传递默认值和校验，代表前端必须传,一般都写校验写法
        id: int = Query(..., description="用户id", gt=0, le=100),#校验的时候去写默认值
        # name: str = "haha",  #默认值可以写，代表前端可传可不传，但是一般不这么写，校验的时候再去写默认值
        name: str = Query(default="yangmi", description="用户名称", min_length=2),#校验的时候去写默认值
        age: int = Query(..., description="年龄", gt=0, le=100) #默认值也是在校验当中去写
):
    return {"id":id, "name":name,"age":age}


# todo 三、接收请求体参数 一般都是传递json 还有表单类型（让用户页面输入或者上传文件用的多）
# 这里就不能用get请求 我们就没办法用浏览器去做测试了，浏览器输入回车是普通的get请求
# 请求体参数要么post要么put
#任何参数考虑三个点
#1、前端怎么传
#2、后端怎么接
#3、后端怎么校验(分两层考虑 一、请求体参数使用Body  二、请求体参数当中的键值对使用pydantic来做校验)

from pydantic import BaseModel, Field

class User(BaseModel):
    name: str = Field(..., description="用户名称", min_length=2)
    age: int = Field(..., description="年龄", gt=0, le=100)


@app.post("/testbody")
def testbody(
    user: User = Body(..., description="请求参数用户信息")
):
    #因为接收了请求体参数，会把json串进行反序列化，反序列化变成python的数据，框架会自动把json串变成字典类型
    #Body是用来限定user整体必须是请求体参数
    #默认请求体参数我们如果不用pydantic做校验，会反序列化为字典
    #如果想限定user当中的键，就必须用pydantic来做校验，一旦使用pydantic类来校验注解类型，那么user就变成了pydantic对象不是字典

    print(user,type(user))
    return {"user":user} #返回的时候返回的是字典 对象 无所谓因为都会默认序列化成json串，长相是一样的

if __name__ == '__main__':
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )