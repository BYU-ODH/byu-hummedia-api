from datetime import datetime
from os.path import splitext
from models import connection
from flask import Response, jsonify
from helpers import Resource, mongo_jsonify, parse_npt, resolve_type, uri_pattern, bundle_400, action_401, is_enrolled
from mongokit import ObjectId, cursor
from urlparse import urlparse, parse_qs
import clients, config

db=connection.hummedia
ags=db.assetgroups
assets=db.assets
annotations=db.annotations
users=db.users

class UserProfile(Resource):
    collection=users
    model=users.User
    namespace="hummedia:id/user"
    endpoint="account"

    def auth_filter(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            bundle=self.acl_filter(atts['username'],bundle)
            self.bundle=bundle
        return self.bundle
    
    def set_disallowed_atts(self):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts=['role','superuser']
        
    def acl_filter(self,username="unauth",bundle=None):
        if not bundle:
            bundle=self.bundle
        if type(bundle)==cursor.Cursor:
            bundle=list(bundle)
            for obj in bundle[:]:
                if obj["username"] != username:
                    bundle.remove(obj)
        elif bundle["username"] != username:
                bundle={}
        return bundle

    def acl_write_check(self,bundle=None):
        from auth import get_profile
        atts=get_profile()
        return atts['superuser']

    def post(self,pid=None):
        if self.acl_write_check():
            self.bundle=self.model()
            if not pid:
                if "username" in self.request.json:
                    self.bundle["_id"]=ObjectId(self.request.json.username)
                else:
                    return bundle_400()
            else:
                self.bundle["_id"]=ObjectId(pid)
            self.preprocess_bundle()
            self.set_attrs()
            return self.save_bundle()
        else:
            return action_401()
    
    def set_query(self):
        q={}
        if self.request:
            if self.request.args.get("oauth",False):
                q["oauth"][self.request.args.get("provider")]=self.request.args.get("provider_account")
            elif self.request.args.get("email",False):
                q["email"]=self.request.args.get("email")
        else:
            q["oauth"][self.manual_request["provider"]]=self.manual_request["provider_id"]
        return q
      
class MediaAsset(Resource):
    collection=assets
    model=assets.Video
    namespace="hummedia:id/video"
    endpoint="video"
    override_only_triggers=['enrollment']
    
    def set_disallowed_atts(self):
        self.disallowed_atts=["dc:identifier","pid","dc:type"]
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_query(self):
        q={}
        v=self.request.args.get("q",False)
        if v:
            cire={'$regex':'.*'+v+'.*', '$options': 'i'}
            q["$or"]=[{"ititle":cire},
            {"@graph.ma:description":cire},
            {"@graph.ma:hasKeyword":cire}
            ]
        else:
            if any(x in self.request.args for x in ['yearfrom', 'yearto']):
                q["@graph.ma:date"]={}
                if "yearfrom" in self.request.args: 
                    q["@graph.ma:date"]["$gte"]=int(self.request.args.get("yearfrom"))
                if "yearto" in self.request.args and self.request.args.get("yearto").strip()!="": 
                    q["@graph.ma:date"]["$lte"]=int(self.request.args.get("yearto"))
            elif "ma:date" in self.request.args:
                q["@graph.ma:date"]=int(self.request.args.get("ma:date"))
            for (k,v) in self.request.args.items():
                cire={'$regex':'.*'+v+'.*', '$options': 'i'}
                if k == "ma:title":
                    q["ititle"]=cire
                elif k in ["ma:description","ma:hasKeyword"]:
                    q["@graph."+k]=cire
                elif k not in ["yearfrom","yearto","ma:date","part","inhibitor"]:
                    q["@graph."+k]=v
        return q
        
    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        for d in self.bundle:
            alist.append(self.model.make_part(d["@graph"],config.APIHOST,self.request.args.get("part","details")))
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']

    def read_override(self,obj,username,role):
        allowed=False
        for parent in obj['@graph']['ma:isMemberOf']:
            id=parent['@id'] if '@id' in parent else None
            c=ags.find_one({"_id":ObjectId(id)})
            if c:
                if is_enrolled(username,c):
                    allowed=True
        return allowed
        
    def serialize_bundle(self,payload):
        if self.request.args.get("annotations",False):
            a=annotations.find({"@graph.dc:relation":payload["_id"]})
            payload["@graph"]["annotations"]=[]
            for ann in a:
                new_ann=Annotation(bundle=ann["@graph"],client=self.request.args.get("client",None))
                payload["@graph"]["annotations"].append(new_ann.part.data)
        payload["@graph"]["resource"]=uri_pattern(payload["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)    
        payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
        payload["@graph"]["url"]=[]
        if payload["@graph"]["type"]=="humvideo":
            prefix=config.HOST+"/"+self.endpoint
            needs_ext=True
        elif payload["@graph"]["type"]=="yt":
            prefix="http://youtu.be"
            needs_ext=False
        for location in payload["@graph"]["ma:locator"]:
            if needs_ext:
                ext=location["ma:hasFormat"].split("/")[-1]
                loc=".".join([location["@id"],ext])
            else:
                loc=location["@id"]
            payload["@graph"]["url"].append(uri_pattern(loc,prefix))
        return mongo_jsonify(payload["@graph"])

    def set_attrs(self):
        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in self.disallowed_atts:
                if k in ["ma:features","ma:contributor"]:
                    for i in v:
                        self.bundle["@graph"][k].append({"@id":i["@id"],"name":unicode(i[k])})
                elif k in ["ma:isCopyrightedBy","ma:hasGenre"]:
                    self.bundle["@graph"][k]={"@id":v["@id"],"name":unicode([k]) }
                    self.bundle["@graph"][k]=ObjectId(v)
                elif self.model.structure['@graph'][k]==type(u""):
                    self.bundle["@graph"][k]=unicode(v)
                elif k=="ma:title":
                    self.bundle["ititle"]=unicode(v).lower()
                    self.bundle["@graph"]["ma:title"]=unicode(v)
                elif self.model.structure['@graph'][k]==type(2):
                    self.bundle["@graph"][k]=int(v)
                elif self.model.structure['@graph'][k]==type(2.0):
                    self.bundle["@graph"][k]=float(v)
                elif type(self.model.structure['@graph'][k])==type([]):
                    self.bundle["@graph"][k]=[]
                    for i in v:
                        if k=="ma:isMemberOf":
                            membership={}
                            for (g,h) in i.items():
                                membership[g]=ObjectId(h) if g=="@id" else h
                            self.bundle["@graph"][k].append(membership)
                        else:
                            self.bundle["@graph"][k].append(i)    
                else: 
                    self.bundle["@graph"][k]=v
            elif k=="url":
                if type(v)!=type([]):
                    v=[v]
                self.bundle["@graph"]["ma:locator"]=[]
                for i in v:
                    p=urlparse(i)
                    if p[1]=="youtube.com":
                        path=parse_qs(p[4])["v"]
                    else:
                        path=p[2]
                    path=path.split("/")[-1]
                    file,ext=splitext(path)
                    ext=ext.replace(".","")
                    loc={"@id":file,"ma:hasFormat":"video/"+ext}
                    if ext=="mp4":
                        loc["ma:hasCompression"]={"@id":"http://www.freebase.com/view/en/h_264_mpeg_4_avc","name": "avc.42E01E"}
                    elif ext=="webm":
                        loc["ma:hasCompression"]={"@id":"http://www.freebase.com/m/0c02yk5","name":"vp8.0"}
                    self.bundle["@graph"]["ma:locator"].append(loc)

    def delete(self,id):
        from auth import get_profile
        atts=get_profile()
        if atts['superuser']:
            self.bundle=self.model.find_one({'_id': ObjectId(id)})
            return self.delete_obj()
        else:
            return action_401()
            
class AssetGroup(Resource):
    collection=ags
    model=ags.AssetGroup
    namespace="hummedia:id/collection"
    endpoint="collection"
    override_only_triggers=['enrollment']
    
    def set_query(self):
        q={"@graph.dc:creator":self.request.args.get("dc:creator")} if "dc:creator" in self.request.args else {}
        return q
        
    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        if self.bundle:
            for d in self.bundle:
                d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
                d["@graph"]["type"]=resolve_type(d["@graph"]["dc:type"])
                alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
        
    def read_override(self,obj,username,role):
        if role=="student" and is_enrolled(username,obj):
            return True
        else:
            return False
            
    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']
        
    def serialize_bundle(self,payload):
        if payload:
            v=assets.find({"@graph.ma:isMemberOf.@id":payload["_id"]})
            payload["@graph"]["videos"]=[]
            from auth import get_profile
            atts=get_profile()
            if not is_enrolled(atts['username'],payload):
                v=self.auth_filter(v)
            for vid in v:
                if self.request.args.get("full",False):
                    resource=uri_pattern(vid["@graph"]["pid"],config.APIHOST+"/video")    
                    vid["@graph"]["type"]=resolve_type(vid["@graph"]["dc:type"])
                    vid["@graph"]["resource"]=resource
                    payload["@graph"]['videos'].append(vid["@graph"])
                else:
                    payload["@graph"]["videos"].append(assets.Video.make_part(vid["@graph"],config.APIHOST,self.request.args.get("part","details")))
            payload["@graph"]["type"]=resolve_type(payload["@graph"]["dc:type"])
            return mongo_jsonify(payload["@graph"])
        else:
            return mongo_jsonify({})
            
    def set_disallowed_atts(self):
        self.disallowed_atts=["dc:identifier","pid","dc:type"]
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_attrs(self):
        if "type" in self.request.json:
            self.bundle["@graph"]["dc:type"]="hummedia:type/"+self.request.json["type"]
        for (k,v) in self.request.json.items():
            if k in self.model.structure['@graph'] and k not in self.disallowed_atts:
                self.bundle["@graph"][k]=unicode(v) if k in ["dc:title","dc:description"] else v

class Annotation(Resource):
    collection=annotations
    model=annotations.AnnotationList
    namespace="hummedia:id/annotation"
    endpoint="annotation"
    
    def set_query(self):
        if self.request.args.get("dc:relation",False):
            q={"@graph.dc:relation":ObjectId(self.request.args.get("dc:relation"))}
        elif self.request.args.get("dc:creator",False):
            q={"@graph.dc:creator":self.request.args.get("dc:creator")}
        else:
            q={}
        return q
        
    def get_list(self):
        alist=[]
        self.bundle=self.auth_filter()
        for d in self.bundle:
            d["@graph"]["resource"]=uri_pattern(d["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
            alist.append(d["@graph"])
        return mongo_jsonify(alist)
        
    def set_resource(self):
        self.bundle["@graph"]["resource"]=uri_pattern(self.bundle["@graph"]["pid"],config.APIHOST+"/"+self.endpoint)
        
    def client_process(self):
        c=clients.lookup[self.request.args.get("client")]()
        m=assets.find_one(self.bundle["@graph"]["dc:relation"])
        m["@graph"]["resource"]=uri_pattern(m["@graph"]["pid"],config.APIHOST+"/video")
        m["@graph"]["type"]=resolve_type(m["@graph"]["dc:type"])
        m["@graph"]["url"]=[]
        for url in m["@graph"]["ma:locator"]:
            if m["@graph"]["type"]=="humvideo":
                host=config.HOST+"/video"
                ext="."+url["ma:hasFormat"].replace("video/","")
            elif m["@graph"]["type"]=="yt":
                host="http://youtu.be"
                ext=""
            m["@graph"]["url"].append(uri_pattern(url["@id"]+ext,host))
        return c.serialize(self.bundle["@graph"],m["@graph"])

    def preprocess_bundle(self):
        self.bundle["@graph"]["dc:identifier"] = "%s/%s" % (self.namespace,str(self.bundle["_id"]))
        self.bundle["@graph"]["pid"] = str(self.bundle["_id"])
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.bundle["@graph"]["dc:creator"]=atts['username']
        
    def serialize_bundle(self,payload):
        return mongo_jsonify(payload["@graph"])
        
    def set_disallowed_atts(self):
        from auth import get_profile
        atts=get_profile()
        if not atts['superuser']:
            self.disallowed_atts.append("dc:creator")
    
    def set_attrs(self):
        if "client" in self.request.args:
            c=clients.lookup[self.request.args.get("client")]()
            packet=c.deserialize(self.request)
        else:
            packet=self.request.json
        for (k,v) in packet.items():
            if k=="dc:relation":
                self.bundle["@graph"][k]=ObjectId(v)
            elif k=="dc:title":
                self.bundle["@graph"]["dc:title"]=unicode(v)
            elif k=="vcp:playSettings":
                for (i,j) in v.items():
                    if i=="vcp:frameRate":
                        self.bundle["@graph"]["vcp:playSettings"][i]=float(j)
                    elif i=="vcp:videoCrop":
                        self.bundle["@graph"]["vcp:playSettings"][i]=j
                    else:
                        self.bundle["@graph"]["vcp:playSettings"][i]=int(j)
            elif k=="vcp:commands":
                self.bundle["@graph"]["vcp:commands"]=[]
                for i in v:
                    self.bundle["@graph"]["vcp:commands"].append(i)
            else:
                self.bundle["@graph"][k]=v

