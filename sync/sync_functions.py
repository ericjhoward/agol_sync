def step_delete(layer,id_list,step_number=1000,results={'addResults':[],'updateResults':[],'deleteResults':[]}):
    start = 0
    print(layer.properties.name,"- Deletes")
    while start< len(id_list):
        print(start,start+step_number)
        deletestring= """['"""+"""','""".join(id_list[start:start+step_number])+"""']"""
        results['deleteResults']+=(layer.edit_features(deletes=deletestring,use_global_ids=True,rollback_on_failure=False)['deleteResults'])
        start+=step_number
    return results    
        
    

def step_update(dataset,layer,step_number=2000,results={'addResults':[],'updateResults':[],'deleteResults':[]}):
    start=0    
    print(layer.properties.name,"- Updates")
    while start< len(dataset):
        print(start,start+step_number)
        results['updateResults']+=(layer.edit_features(updates=dataset[start:start+step_number],use_global_ids=True,rollback_on_failure=False)['updateResults'])
        start+=step_number
    return results


def step_add(dataset,layer,step_number=2000,results={'addResults':[],'updateResults':[],'deleteResults':[]}):
    start=0    
    print(layer.properties.name,"- Adds")
    while start< len(dataset):
        print(start,start+step_number)
        results['addResults']+=(layer.edit_features(adds=dataset[start:start+step_number],use_global_ids=True,rollback_on_failure=False)['addResults'])
        start+=step_number
    return results


        
def data_dump_month(flc,data,top_folder):
    import os
    import time
    '''Sub Function for ReplicaSYNC - writes sync data to text file.
    Will be useful for getting edits in case of errors
        -FLC: Feature Layer Collection - Used only for naming file
        -data: JSON data returned by SYNC
        -topfolder: where the data is to be housed
    This function will make a Year-Month folder structure then make a subfolder
      for each different FLC that is sync'd'''
    current_month = time.strftime("%Y_%m")
    name = flc.url.split('/')[-2]
    month_folder = os.path.join(top_folder,current_month)
    if not os.path.exists(month_folder):
        os.mkdir(month_folder)
    sub_folder = os.path.join(top_folder,current_month,name)
    if not os.path.exists(sub_folder):
        os.mkdir(sub_folder)
    data_txt = os.path.join(sub_folder,name+time.strftime("_%Y%m%d_%H%M%S.txt"))
    with open(data_txt,'w') as data_filer:
        data_filer.write(json.dumps(data))

def replica_sync(flc,replica_id,dump_folder):
    """for sync of specific replica
    need to have a FeatureLayerCollection object and a replica ID
    always load this into a variable - for example:
    MyUpdates = replicaSync(FeatureLayerCollection,'l123lk2j45lk3')"""
    server_gens = flc.replicas.get(replica_id)['layerServerGens']
    json_updates = flc.replicas.synchronize(replica_id = replica_id,
                    transport_type='esriTransportTypeEmbedded', 
                    replica_server_gen = None, 
                    return_ids_for_adds = False,
                    edits = None,
                    return_attachment_databy_url = False,
                    asynchronous = False, 
                    sync_direction = 'download',
                    sync_layers=server_gens,
                    edits_upload_id=None, 
                    edits_upload_format=None,  
                    data_format='json',
                    rollback_on_failure=True)
    data_dump_month(flc,json_updates,dump_folder)
    return json_updates

def parse_json_response(json_response):
    suc_add = True
    fails_add = []
    for res in json_response['addResults']:
        if res['success']==False:
            suc_add=False
            fails_add.append(res['globalId'])
            
    suc_upd = True
    fails_upd = []
    for res in json_response['updateResults']:
        if res['success']==False:
            suc_upd=False
            fails_upd.append(res['globalId'])           
    
    suc_del = True
    fails_del = []
    for res in json_response['deleteResults']:
        if res['success']==False:
            suc_del=False
            fails_del.append(res['globalId'])   
            
    suc_total = True
    if suc_add==False or suc_upd==False or suc_del==False:
        suc_total=False
        errors = ''
        if suc_add == False:
            errors+="Add Errors: "+','.join(fails_add)+" | "
        if suc_upd == False:
            errors+="Update Errors: "+','.join(fails_upd)+" | "
        if suc_del == False:
            errors+="Delete Errors: "+','.join(fails_del)+" | "
            
    return (suc_total,errors)
    

def applyUpdates(syncJSONedits,destlayer,loglist):
    import time
    '''by layer: needs to take sync object and go into index
    syncJSONedits needs to be UPDjson['edits'][INDEX]['features']'''
    JSONupdates = syncJSONedits['updates']
    for feature in JSONupdates:
        feature['attributes']['GlobalID']='{'+feature['attributes']['GlobalID']+'}'

    JSONadds = syncJSONedits['adds']
    
    JSONdeletes = []
    for glob in syncJSONedits['deleteIds']:
            JSONdeletes.append('{'+glob+'}')
    JSONdeletestring= """['"""+"""','""".join(JSONdeletes)+"""']"""
    
    print("====="+destlayer.properties.name+"=====")
    print("\tAdds: "+str(len(JSONadds)))
    print("\tUpdates: "+str(len(JSONupdates)))
    print("\tDeletes: "+str(len(JSONdeletes)))
    try:
        results  = destlayer.edit_features(adds=JSONadds,updates=JSONupdates,deletes=JSONdeletestring,use_global_ids=True,rollback_on_failure=False)
        (success,errors) = parse_json_response(results)
        loglist.append([destlayer.properties.name,time.strftime("%m/%d/%Y %H:%M"),len(JSONadds),len(JSONupdates),len(JSONdeletes),success,errors])
        return results
    except:
        print('error - trying to step through process')
        outresults={'addResults':[],'updateResults':[],'deleteResults':[]}
        step_add(JSONadds,destlayer,2000,outresults)
        step_update(JSONupdates,destlayer,2000,outresults)
        step_delete(destlayer,JSONdeletes,outresults)
        
        (success,errors) = parse_json_response(outresults)
        loglist.append([destlayer.properties.name,time.strftime("%m/%d/%Y %H:%M"),len(JSONadds),len(JSONupdates),len(JSONdeletes),success,errors])
        return outresults


