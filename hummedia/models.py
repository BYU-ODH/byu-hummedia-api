from mongokit import Document, Connection, CustomType, OR
from config   import MONGODB_HOST, MONGODB_PORT, MONGODB_DB
import datetime

class IsoDate(CustomType):
    mongo_type = unicode
    python_type = datetime.datetime
    init_type = None

    def to_bson(self, value):
        if value is not None:
            return unicode(datetime.datetime.strftime(value,'%Y-%m-%d'))

    def to_python(self, value):
        if value is not None:
		return datetime.datetime.strptime(value, '%Y-%m-%d')

connection=Connection(MONGODB_HOST, MONGODB_PORT)

@connection.register
class User(Document):
    __collection__="users"
    __database__=MONGODB_DB
    use_schemaless=True
    structure={
        "username": basestring,
        "email": basestring,
        "firstname": unicode,
        "lastname": unicode,
        "role": basestring,
        "userid": basestring,
        "superuser": bool,
        "ta":bool,
        "preferredLanguage": basestring,
        "oauth": {
            "google": {"id": basestring, "email": basestring, "access_token": list},
            "facebook": dict,
            "twitter": dict
        }
    }
    required_fields=["username","email"]
    default_values={"username":"","email":"","preferredLanguage":"en","role":"student","superuser":False,"ta":False}
    
@connection.register
class Clip(Document):
    __collection__ = 'clips'
    __database__ = MONGODB_DB
    use_schemaless = True
    structure = {
        #'_id': basestring, # unique id of clip
        'userid': basestring, # ID of user
        'mediaid': basestring, # ID of video
        'name': basestring, # name of clip
        'start': float, # start time (seconds)
        'end': float # end time (seconds)
    }
    # 'end' is optional - clips will continue playing from bookmark if undefined.
    required_fields = ['userid', 'mediaid', 'name', 'start']

@connection.register
class AnnotationList(Document):
    __collection__="annotations"
    __database__=MONGODB_DB
    use_schemaless=True
    structure= {
        "@context": dict,
        "@graph": {
            "pid": basestring,
            "dc:identifier":basestring,
            "dc:title": unicode,
            "dc:relation": basestring,
            "dc:creator": basestring,
            "dc:date":IsoDate(),
            "vcp:playSettings": dict,
            "vcp:commands":[dict],
            "dc:coverage": basestring,
            "dc:rights": {
                "read": list,
                "write": list
            }
        }
    }
    required_fields=["@context","@graph.dc:creator",
                     "@graph.dc:date","@graph.dc:title"]
    default_values={
        "@context": {
            "dc":"http://purl.org/dc/",
            "oa":"http://www.w3.org/ns/oa#",
            "oax":"http://www.w3.org/ns/openannotation/extension/",
            "vcp":"http://cvp.byu.edu/namespace/",
            "dc:identifier": "@id"
          },
        "@graph.dc:creator":"Hummedia",
        "@graph.dc:title":u"New Hummedia Annotation",
        "@graph.dc:coverage":"public",
        "@graph.dc:date":datetime.datetime.utcnow(),
        "@graph.vcp:playSettings": {
            "vcp:showTranscript": False,
            "vcp:audioOffset":0,
            "vcp:videoOffset":0,
            "vcp:videoCrop":0,
            "vcp:frameRate":23.976
        }     
    }

@connection.register
class AssetGroup(Document):
    __collection__="assetgroups"
    __database__=MONGODB_DB
    use_schemaless=True
    structure= {
        "@context": dict,
        "@graph": {
            "pid": basestring,
            "authorized": bool,
            "dc:identifier":basestring,
            "dc:type": basestring,
            "dc:title": unicode,
            "dc:description": unicode,
            "dc:relation": [basestring],
            "dc:creator": basestring,
            "dc:date":IsoDate(),
            "dc:coverage": basestring,
            "dc:rights": {
                "read": list,
                "write": list
            }
        }
    }
    required_fields=["@context","@graph.dc:type","@graph.dc:creator",
                     "@graph.dc:date","@graph.dc:title"]
    default_values={
        "@context": {
                "authorized": False,
                "dc": "http://purl.org/dc/elements/1.1/",
                "hummedia": "http://humanities.byu.edu/hummedia/",
                "dc:identifier": "@id",
                "dc:type": "@type"
        },
        "@graph.dc:creator":"Hummedia",
        "@graph.dc:relation":[],
        "@graph.dc:title":u"New Hummedia Collection",
        "@graph.dc:type":"hummedia:type/course_collection",
        "@graph.dc:date":datetime.datetime.utcnow(), 
        "@graph.dc:coverage":"private"
    }



@connection.register
class Video(Document):
    __collection__="assets"
    __database__=MONGODB_DB
    use_schemaless=True
    structure= {
        "@context": dict,
        "@graph": {
            "dc:creator": basestring,
            "dc:date": IsoDate(),    
            "dc:identifier": basestring,
            "dc:type": basestring,
            "dc:coverage": basestring,
            "dc:rights": {
                "read": list,
                "write": list
            },
            "dc:hlr": bool,
            "dc:callnumber": unicode,
            "dc:expirationdate": int,
            "dc:physicallocation": unicode,
            "dc:lastviewed": IsoDate(),
            "ma:averageBitRate": int,
            "ma:isCopyrightedBy": {
                "@id": basestring,
                "name": unicode
            },
            "ma:date": int,
            "ma:description": unicode,
            "ma:duration": int,
            "ma:features": [
                { 
                    "@id": basestring,
                    "name": unicode
                }
            ],
            "ma:frameHeight": int,
            "ma:frameRate": OR(float,int),
            "ma:frameSizeUnit": basestring,
            "ma:frameWidth": int,
            "ma:hasContributor": [
                {
                    "@id": basestring,
                    "name": unicode  
                }
            ],
            "ma:hasGenre": {
                "@id": basestring,
                "name": unicode
            },
            "ma:hasLanguage": [basestring],
            "ma:isMemberOf": [dict],
            "ma:isRelatedTo": [basestring],
	    "ma:hasRelatedResource": [dict],
            "ma:hasKeyword": [basestring],
            "ma:hasPolicy": [basestring],
            "ma:locator": [
                {
                    "location":basestring,
                    "ma:hasFormat":basestring,
                    "ma:hasCompression": {
                        "@id": basestring,
                        "name": basestring
                    }
		}
            ],
            "ma:title": unicode
        }
    }
    required_fields=["@context","@graph.dc:creator","@graph.dc:date","@graph.dc:type","@graph.ma:date","@graph.ma:hasLanguage","@graph.ma:title", "@graph.ma:duration"]
    default_values={
        "@context": {
            "dc": "http://purl.org/dc/elements/1.1/",
            "dc:identifier": "@id",
            "dc:type": "@type",
            "ma": "http://www.w3.org/ns/ma-ont/",
            "hummedia": "http://humanities.byu.edu/hummedia/"
        },            
        "@graph.dc:creator":"Hummedia",
        "@graph.dc:date": datetime.datetime.utcnow(),
        "@graph.dc:type": "hummedia:type/humvideo",
        "@graph.ma:title":u"New Hummedia Video",
        "@graph.ma:date": 1900,
	"@graph.ma:duration": 0,
        "@graph.ma:hasLanguage":["en"],
        "@graph.dc:coverage":"private",
        "@graph.ma:frameRate": 23.976,
        "@graph.ma:averageBitRate":768000,
        "@graph.ma:frameHeight": 360,
        "@graph.ma:frameWidth": 640,
        "@graph.ma:frameSizeUnit":"px"
    }

    def make_part(self,vid,host,part):
        from helpers import uri_pattern, resolve_type
        from config import HOST
        resource=uri_pattern(vid.get("pid"),host+"/video")
        thepart={"ma:title":vid["ma:title"],"pid":vid.get("pid"),"resource":resource}
        thepart['type'] = resolve_type(vid['dc:type'])
        if part!="snippet":
            thepart["fromYt"]=[]
            thepart["ma:image"]=[]
            for location in vid["ma:locator"]:
                if location['@id'] is None:
                    continue
                if resolve_type(vid["dc:type"])=="humvideo":
                    poster=uri_pattern(location["@id"]+".jpg",HOST+"/posters")
                    thumb=uri_pattern(location["@id"]+"_thumb.jpg",HOST+"/posters")
                    thepart["ma:image"].append({"poster":poster,"thumb":thumb})
                elif resolve_type(vid['dc:type'])=='humaudio':
                    pass
                else:
                    thepart["ma:image"].append({"ytId":location["@id"]})
                    thepart["fromYt"].append(location["@id"])
            for att in ["ma:date","ma:description","ma:hasLanguage","ma:hasPolicy", "ma:isMemberOf"]:
                thepart[att]=vid.get(att)
            for annot in thepart["ma:isMemberOf"]:
                coll=connection[MONGODB_DB].assetgroups.find_one({"_id":annot["@id"]})
		if coll is not None:
	            annot["title"]=coll["@graph"]["dc:title"]
        return thepart
