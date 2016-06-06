import io
import json
from .. import config
from .. import vtt

def upload_single_file_and_assert(app_instance, filename):
  with open(filename) as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app_instance.post('/batch/audio/ingest', data=data)

  data = json.loads(response.data)
  item = data[0]

  new_filename = item['ma:locator'][0]['@id']

  file = open(config.MEDIA_DIRECTORY + new_filename, 'r')
  orig = open(filename, 'r')

  assert item['ma:title'] == 'Coin dropped on wooden floor'
  assert item['ma:date'] == 2007
  assert item['pid'] is not None
  assert {'@id': '', 'name': 'Ezwa'} in item['ma:hasContributor']
  assert len(data) == 1, "More than one audio file added."
  assert response.status_code == 200
  assert orig.read() == file.read()

def test_upload_mp3_without_date_id3(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  with open(ASSETS + 'stapler.mp3') as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  assert response.status_code == 200

def test_upload_mp3_without_any_id3(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  with open(ASSETS + 'stapler-tagless.mp3') as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  assert response.status_code == 200

def test_upload_mp3(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  upload_single_file_and_assert(app, ASSETS + 'coin.mp3')

def test_upload_bad_file(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  with open(ASSETS + 'blank') as f:
    data = {
        'audio[]': [(f, 'blank')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  assert response.status_code == 400

def test_upload_mp3_faculty(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["FACULTY"])
  with open(ASSETS + 'coin.mp3') as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  assert response.status_code == 401, "Non-superuser faculty can upload file"

def test_upload_mp3_restricted(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["STUDENT"])
  response = None

  with open(ASSETS + 'coin.mp3') as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  assert response.status_code == 401, "Student can upload MP3"

def test_upload_multiple_mp3s(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS["SUPERUSER"])
  with open(ASSETS + 'coin.mp3') as f1, open(ASSETS + 'stapler.mp3') as f2:
    data = {
        'audio[]': [(f1, 'audio.mp3'), (f2, 'audio2.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 2

def test_upload_wrong_form_name(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS['SUPERUSER'])
  with open(ASSETS + 'coin.mp3') as f:
    data = {
        'thing': [(f, 'coin.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)
    assert response.status_code == 400

def test_retrieve_audio_with_bad_collection(ASSETS, ACCOUNTS, app):
  app.login(ACCOUNTS['SUPERUSER'])

  with open(ASSETS + 'stapler.mp3') as f:
    data = {
        'audio[]': [(f, 'audio.mp3')]
    }
    response = app.post('/batch/audio/ingest', data=data)

  data = json.loads(response.data)
  pid = data[0]['pid']

  c = app.post('/collection', data=json.dumps({}), headers={'Content-Type': 'application/json'})
  data = json.loads(c.data)
  col_pid = data['pid']

  # attach audio to collection
  membership = [{"collection":{"id":col_pid,"title":"Something"},"videos":[pid]}]
  membership_result = app.post('/batch/video/membership', data=json.dumps(membership), headers={'Content-Type': "application/json"})
  assert membership_result.status_code is 200

  data = json.loads(app.get('/video/' + pid).data)
  assert(len(data['ma:isMemberOf']) is 1)

  # delete the collection
  app.delete('/collection/' + col_pid)
  result = app.get('/video/' + pid)
  data = json.loads(result.data)
  assert(len(data['ma:isMemberOf']) is 0)
