# coding: UTF-8
from __future__ import print_function

import boto3
import json,logging,re,datetime
from boto3.dynamodb.conditions import Key, Attr
import uuid, hashlib #token生成向け

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

#LambdaFunctionのエントリポイント
def lambda_handler(event, context):

    logger.info("Received event: " + json.dumps(event, indent=2))
    
    #以下のメソッドは認証が必要
    AuthorizationHeader = event["headers"]["Authorization"]

    if re.search(r"Bearer", AuthorizationHeader) is None :
        return respond("401",'{"message": "no Authorization"}')
        
    #ヘッダからTokenを取り出す・・・ロジックイマイチ
    token = AuthorizationHeader.replace("Bearer","").replace(" ","")
    #tokenをキーにDynamoからitemを取得    
    item = get_daynamo_item("token","token",token)
    logger.info(item)
    if item.has_key("Item") == False :
        return respond("401",'{"message": "invalid token"}')
    
    if event["httpMethod"] == "PUT": #Status更新
        return put(event, context, item["Item"]["userid"],item["Item"]["name"] )
    elif event["httpMethod"] == "GET" :
        return get(event, context, item["Item"]["userid"])
    else :
        return respond("400",'{"message":"not expected method"}') 
        
#PutメソッドでサービスをCallされた際の挙動
def put(event, context, userid, name) :

    body_object = json.loads(event["body"]) #eventのbodyにはJsonのStringが入っているので、Parseする
    try :
        #登録実施, 既存の予定があれば上書きする
        boto3.resource('dynamodb').Table("status").put_item(
            Item = {
                "userid" : userid,
                "InBuissiness" : body_object["InBuissiness"],
                "Comment":  body_object["Comment"],
                "name" : name
            }
        )
        
        #この処理は追って、移動するする予定
        #ログテーブルへの格納登録実施
        boto3.resource('dynamodb').Table("status-log").put_item(
            Item = {
                "userid" : userid,
                "datetime" : str(datetime.datetime.today()),
                "InBuissiness" : body_object["InBuissiness"],
                "Comment":  body_object["Comment"]
            }
        )        
        #ココまで
        
        
        return respond("200",event["body"])
    except Exception, e:
        logger.info(e)
        return respond("400",'{"message": "user post is faild"}')
        
#GetメソッドでサービスをCallされた際の挙動
def get(event, context, userid) :
    
    #Limit = 1とする事で、最初の1行のみ取得する
    item = boto3.resource('dynamodb').Table('status').query(
        KeyConditionExpression=Key('userid').eq(userid),
        Limit = 1
    )
    logger.info(item)
    
    if item.has_key("Items") == False :
        return respond("400",'{"message": "no status"}')
    else :
        return respond("200", \
            '{"InBuissiness":' + str(item["Items"][0]["InBuissiness"]) +   \
            ' , "Comment": "' + item["Items"][0]["Comment"] + '" }')

#汎用リターン Lambda統合Proxyの場合、この形式のreturnしか受け付けない
def respond(statusCode, res=None):
    return {
        'statusCode': statusCode,
        'body': json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
    }



#汎用データ登録
def get_daynamo_item(table_name, keyName, KeyValue  ):
    return boto3.resource('dynamodb').Table(table_name).put_item(
        Item = {
            "userid" : aa,
            "password" : aa,
            "name" : aa,
            "currenttoken": aa             
        }
    )

#汎用データ取得
def get_daynamo_item(table_name, keyName, KeyValue  ):
    return boto3.resource('dynamodb').Table(table_name).get_item(
            Key={
                 keyName: KeyValue
            }
        )

#汎用レコード Update
def update_dynamo_item(table_name, keyName, keyValue, AttributeName, AttributeValue):
    boto3.resource('dynamodb').Table(table_name).update_item(
                Key = {
                     keyName : keyValue
                },
                AttributeUpdates = {
                     AttributeName:{
                         'Action': 'PUT',
                         'Value': AttributeValue
                     }
                }
    )    