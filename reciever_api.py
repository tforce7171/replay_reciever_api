from flask import Flask, request, make_response
from flask_restful import Api, Resource, reqparse
from flask_cors import CORS
import json
import os
from constant import *
import zipfile
import io
import requests
import time
import base64

app = Flask(__name__)
api = Api(app)
CORS(app)
parser = reqparse.RequestParser()
parser.add_argument('task')

class ReplayData(Resource):
    def post(self):
        data = request.get_json(force = True)
        replay_file_binary = base64.b64decode(data["replay_file_binary"])
        validator = ReplayValidator(data, replay_file_binary)
        if validator is True:
            data["unix_time"] = int(time.time())
            data["conversion_status"] = "in queue"
            data["video_url"] = ""
            del(data["token"], data["replay_file_binary"])
            files = {
                "file": (data["replay_name"], replay_file_binary),
                "json": (None, json.dumps(data))
                }
            response = requests.post(Constant.REPLAY_DATA_URL, files=files)
            return "success"
        else:
            return validator
        return ""

    def get(self):
        response = requests.get(Constant.REPLAY_DATA_URL)
        data = json.loads(response.content)
        return data

class MetaData(Resource):
    def get(self):
        response = requests.get(Constant.REPLAY_DATA_URL)
        datas = json.loads(response.content)
        in_queue_count = 0
        in_process_count = 0
        completed_count = 0
        for data in datas:
            if data["conversion_status"] == "in queue":
                in_queue_count += 1
            elif data["conversion_status"] == "in process":
                in_process_count += 1
            elif data["conversion_status"] == "completed":
                completed_count += 1
        return {"in_queue": in_queue_count, "in_process": in_process_count, "completed": completed_count}

class ReplayFile(Resource):
    def get(self):
        replay_name = request.args.get("replay_name")
        datas = json.loads(requests.get(Constant.REPLAY_DATA_URL).content)
        for data in datas:
            if data["replay_name"] == replay_name:
                params = {"replay_name": replay_name}
                result = requests.get("https://databaseapi7171.herokuapp.com/replay_file", params=params)
                response = make_response()
                response.data = result.content
                response.headers['Content-Disposition'] = 'attachment; filename=' + replay_name
                return response
            else:
                return "No replay matched with a specified replay name"


def ReplayValidator(data, replay_file_binary):
    result = TokenValidator(data)
    if result is not True:
        return result
    result = VersionValidator(replay_file_binary)
    if result is not True:
        return result
    # result = HistoryValidator(data)
    # if result is not True:
    #     return result
    return True

def TokenValidator(data):
    if "token" in data:
        if data["token"] in Constant.TOKENS:
            return True
        else:
            return "Invalid token"
    else:
        return "Json file must have key: token"


def VersionValidator(replay_file_binary):
    replay_file_zip = zipfile.ZipFile(io.BytesIO(replay_file_binary))
    meta_json = json.loads(replay_file_zip.open("meta.json").read().decode())
    replay_version = meta_json["version"]
    result = json.loads(requests.get(Constant.GAME_INFO_URL).content)
    app_version = result["results"][0]["version"]
    if app_version.count('.') == 1:
        app_version = app_version + '.0'
    if app_version == replay_version:
        return True
    else:
        return "The replay version does not match the current game version"

def HistoryValidator(data):
    response = requests.get(Constant.REPLAY_DATA_URL)
    replay_datas = json.loads(response.content)
    for replay_data in replay_datas:
        if replay_data["replay_name"] == data["replay_name"]:
            return "This replay is already in queue or has been converted"
    return True

api.add_resource(ReplayData, "/api/replay_data")
api.add_resource(MetaData, "/api/meta_data")
api.add_resource(ReplayFile, "/api/replay_file")

if __name__ == "__main__":
    app.run(debug = True)
