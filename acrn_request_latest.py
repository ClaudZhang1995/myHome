# _*_ coding:utf-8 _*_

import requests
from requests.auth import HTTPBasicAuth
import json
import os
import operator
import smtplib
from email.mime.text import MIMEText
import logging
import re

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='myapp.log',
                    filemode='a'
                    )
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-8s: %(levelname)-4s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)


class ProjectacrnPullRequest(object):

    def __init__(self, username, userpwd):
        self.base_url = ''
        self.s = requests.Session()
        self.s.auth = HTTPBasicAuth(username, userpwd)

    def send_email(self, subject, content, mail=[]):
        # Send a reminder email
        # 发送邮件
        sender = 'Integration_auto_merge@intel.com'  # 邮件发送人可以为一个虚拟的邮箱（需要加后缀@...com）
        if 'hypervisor' in self.base_url:
            #receivers = ['wenling.zhang@intel.com','nanlin.xie@intel.com', 'yunx.zhang@intel.com','mingyuanx.zhou@intel.com'] + mail
            receivers = ['yunx.zhang@intel.com']
        else:
            receivers = ['yunx.zhang@intel.com']
        msg = MIMEText(content, 'plain', 'utf-8')

        msg['Subject'] = subject
        msg['From'] = sender
        msg['TO'] = ','.join(receivers)
        try:
            s = smtplib.SMTP('smtp.intel.com')
            s.sendmail(sender, receivers, msg.as_string())
            logging.info('send suess')
        except smtplib.SMTPException as err:
            logging.info('Failed to send mail\n %s' % err)

    def acrn_url_info(self, url):
        # request data
        response = self.s.get(url)
        return json.loads(response.text)

    def post_comments(self, url):
        # Post Merge Comments
        body = "Ready to merge"
        response = self.s.post(url, json={'body': body})
        return response.status_code

    def update_statuses(self,url,state,description,context):
        #print("url:"+url)
        target_url=""
        #POST /repos/:owner/:repo/statuses/:sha
        #url=self.base_url+"/statuses/"+head
        response=self.s.post(url,json={'state':state,'target_url':target_url,'description':description,'context':context})   
        update_message="create statuses success" if response.status_code == 201  else "create statuses fail"
        print(update_message)


    def add_label(self,url,labelName):
        headers = {"Authorization": "token 33385712d1129cc19d85d63b885fc152815fab94",
               "Accept": "application/vnd.github.symmetra-preview+json"
               }
        response = self.s.post(url,headers=headers,json={'labels':[labelName]})
        return response.status_code   

    def del_label(self,url):
        headers = {"Authorization": "token 33385712d1129cc19d85d63b885fc152815fab94",
               "Accept": "application/vnd.github.symmetra-preview+json"
               }
        response = self.s.delete(url,headers=headers)
        return response.status_code

    def read_file(self):
        # 读取保存本地的字典文件（以后可以修改为读取数据库）
        try:
            merge_dict_path = 'hynum_dict.json' if 'hypervisor' in self.base_url else 'kenum_dict.json'
            with open(merge_dict_path, 'r') as f:
                merge_num = f.read()
            return eval(merge_num)
        except FileNotFoundError:
            return {}

    def write_file(self, num_list):
        # 保存到本地字典文件 （以后可以保存到数据库）
        merge_dict_path = 'hynum_dict.json' if 'hypervisor' in self.base_url else 'kenum_dict.json'
        with open(merge_dict_path, 'w') as f:
            f.write(str(num_list))

    def determine_doc(self, num):
        # 检查commit的文件是否为doc文档文件
        # 需求：文件不全为doc返回True
        url = self.base_url + '/pulls/%s/files' % num
        try:
            file_list = self.acrn_url_info(url)
            for file in file_list:
                file_type = file['filename'].split('/', 1)[0]
                if file_type != 'doc' and not re.findall(r'.*rst',file['filename']):
                    return True
        except Exception as e:
            logging.info('%s' % e)
        else:
            return False

    def CheckEmail(self,num,commit_url):
        # check email 
        emailMessage = self.acrn_url_info(commit_url)[0]['commit']['message']
        try:
            email1=re.findall(r'Signed-off-by:(.*?@.*?)', emailMessage)
            email2=re.findall(r'Co-Authored-By:(.*?@.*?)', emailMessage)
        except Exception as e:
            logging.error('commit %d no Signed-off-by %s' % (num, e))
            return False
        if not email1 or email2:
            print("doc ,no Signed-off-by and no Co-Authored-By")
            return False
        else:
            return True

    def CheckUerType(self,user,num,statuses_url):
        #check 是否被审批
        user_type=False
        codepath = self.acrn_url_info(self.base_url + '/pulls/' + str(num) + '/files')
        if 'hypervisor' in self.base_url:
            for f in codepath:
                codefile=f['filename']
                #config_tool_modified hypervisor/arch/x86/configs/ 和 hypervisor/scenarios/
                if re.search("hypervisor\/arch\/x86\/configs.*?",codefile) or re.search("hypervisor\/scenarios\/",codefile):
                    #self.update_statuses(statuses_url,"success","Pass","config_tool_modified")
                    label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","config_tool_modified")
                    label_message = "add config_tool_modified success" if label_status == 200 else "add config_tool_modified fail"
                    print(label_message)
                if re.search("^hypervisor\/.*?",codefile):
                    user_type = (user == "dongyaozu" or user == "anthonyzxu")
                elif re.search("^devicemodel\/.*?",codefile):
                    user_type = (user == "anthonyzxu" or user == "ywan170")
                elif re.search("^misc.*?",codefile):
                    user_type = (user == "terryzouhao" or user == "szhen11")
                    if user_type:
                        break
                    if re.search("^misc\/tools\/acrn-crashlog.*?",codefile):
                        user_type = (user == "chengangc" or user == "dizhang417")       
                    elif re.search("^misc\/acrn-config",codefile) or re.search("^misc\/Makefile",codefile):
                        user_type = (user == "binbinwu1")
                    elif re.search("^misc\/efi-stub.*?",codefile):
                        user_type = (user == "jren1")
                    elif re.search("^misc\/tools\/acrnlog",codefile) or re.search("^misc\/tools\/acrntrace",codefile) or re.search("^misc\/acrn-manager",codefile) or re.search("^misc\/acrnbridge",codefile):
                        user_type = (user == "lyan3")
                    else:
                        user_type = (user == "terryzouhao" or user == "szhen11")
                elif re.search(".*?acrn-config",codefile) or re.search(".*?Makefile",codefile):
                     user_type = (user == "binbinwu1")
                else:
                    user_type = (user == "dongyaozu" or user == "anthonyzxu")
                if user_type:
                    break
        else: 
            user_type = (user == 'yakuizhao')
        if user_type:
            print("approve:true")
        else:
            print("approve:false")
        return user_type

    def TrackenOn(self, num, commit_url, html_url):
        for messages in self.acrn_url_info(commit_url): 
            TrackedOnFlag = True
            # 检查是否TrackOn
            try:
                message = messages['commit']['message']
                print('message:'+message)
                me_list = re.findall(r'Tracked-On:.*?(\d+)', message) if 'hypervisor' in self.base_url else re.findall(r'Tracked-On: ?projectacrn/acrn-hypervisor.*?(\d+)',message)
                mail = re.findall(r'Signed-off-by:(.*?@.*?)', message)
            except Exception as e:
                logging.error('commit %d link is error %s' % (num, e))
                TrackedOnFlag = False
                break
            if me_list:
                if not mail:
                    print("no Signed-off-by")
                    subject = 'Waring: NO Tracked-On for PR %d' % num
                    content = """Warning: No "Tracked-On" info in: %s \n \nAppreciated your contribution to ACRN project!\nDue to latest Continuous Integration (CI)process change, we are asking each patch owner to provide additional "Tracked-On" information be added in their patch comment log.\nThis new "Tracked-On" field is used to provide project traceability, any code change must be mapped to either a feature or a bug in the future.\nThe new process:\n1. Submit a new bug in Github if there is no existing bug item in Github.\n2. Cook a patch and go through patch review process (no change)\n3. Input the following commit log for your patch.\nTracked-On:<#IssueNo>\nSigned-off-by: <Username> <mail>\nAfter you finish step 3, we will merge your patch immediately.\nSorry for  the inconvenience due to new CI process change because ACRN project is for embedded IoT which may need strict quality process.\nWe appreciate your understanding and looking forward to your future patch!\nDo not hesitate to contact me if you have any future question.\nBTW: an example patch commit message like this:https://github.com/projectacrn/acrn-hypervisor/pull/1128""" % html_url
                    self.send_email(subject, content)
                    TrackedOnFlag = False
                    break
            else:
                #  no TrackOn info
                print("no tracked on info")
                subject = 'Warning: No Tracked-On information in %d PR' % num
                content = """Warning: No "Tracked-On" info in: %s \n \nAppreciated your contribution to ACRN project!\nDue to latest Continuous Integration (CI)process change, we are asking each patch owner to provide additional "Tracked-On" information be added in their patch comment log.\nThis new "Tracked-On" field is used to provide project traceability, any code change must be mapped to either a feature or a bug in the future.\nThe new process:\n1. Submit a new bug in Github if there is no existing bug item in Github.\n2. Cook a patch and go through patch review process (no change)\n3. Input the following commit log for your patch.\nTracked-On:<#IssueNo>\nSigned-off-by: <Username> <mail>\nAfter you finish step 3, we will merge your patch immediately.\nSorry for the inconvenience due to new CI process change because ACRN project is for embedded IoT which may need strict quality process.\nWe appreciate your underst anding and looking forward to your future patch!\nDo not hesitate to contact me if you have any future question.\nBTW: an example patch commit message like this:https://github.com/projectacrn/acrn-hypervisor/pull/1128""" % html_url
                self.send_email(subject, content, mail)                
                TrackedOnFlag = False
                break
            issues_num = int(me_list[0])
            #该路径下没得External_System_ID
            issues_url = "https://api.github.com/repos/projectacrn/acrn-hypervisor/issues/%d/comments" % issues_num
            try:
                # 有TranckOn查看相关链接
                ext_list = []
                ext_list_flag=''
                body = self.acrn_url_info(issues_url)
                r = requests.get(html_url)
                tracked_on_link=re.findall(r'data-url="https://github.com/projectacrn/acrn-hypervisor/issues/(\d+)"',r.text)
                if not tracked_on_link:
                    logging.info('%s的tracked on is not a complete link' % num)
                    subject = 'Waring: "Tracked-On" link  is incomplete '
                    content = "PR%s's issues %s Tracked-On was incomplete,please provide a complete link.\nlink: %s" % (num, issues_num,html_url)
                    self.send_email(subject, content)
                    TrackedOnFlag = False
                    break
                for message in body:
                    try:
                        ID = message['body']
                    except Exception as e:
                        continue
                    ext_list = re.findall(r'\[External_System_ID\]', ID)
                    if ext_list:
                        ext_list_flag='true'
                if not ext_list_flag:
                    logging.info('%s未找到ID发邮件 需要发送给5个人' % num)
                    subject = 'Waring: No External_System_ID'
                    content = "PR%s's issues %s External_System_ID was not found in the issues of PR \nlink: %s" % (num, issues_num,html_url)
                    self.send_email(subject, content)
                    TrackedOnFlag = False
                    break
            except Exception as e:
                logging.error('issuers链接错误发邮件 需要发送给5个人 %s' % e)
                subject = 'Git Issue link error'
                content = 'Git Issue link error %s, maybe Tracken-On infomation error' % issues_url
                self.send_email(subject, content)
                TrackedOnFlag = False
                break
            TrackedOnFlag = True
        if TrackedOnFlag == True:
            return True
        else:
            return False

    def projectcarn_merge_rebase(self):
        # Parse the json data and execute the method
        read_num_dict = self.read_file()
        merge_num_dict = {}
        trackon_dict = {}
        pulls_json = self.acrn_url_info(self.base_url + '/pulls')
        # merge_url = pulls_json[0]['base']['repo']['merges_url']
        for pull_json in pulls_json:
            CI_FLAG=False
            Coding_Guidelines=False
            CHECK_FLAG=False
            Automerge=False
            Tracked_On_error=False
            Approved_Flag=False
            PremergeTest_Flag=False
            Status_on_hold=False
            Pending_approve=False
            Email_FLAG=False
            delete_email_flag=False
            Misra_Flag=False
            is_MISRA=False
            #STATUS_FLAG=False
            head = pull_json['head']['sha']
            base = pull_json['base']['ref']
            commits_url = pull_json['commits_url']
            num_url = pull_json['url']
            num = pull_json['number']
            comment_url = pull_json['comments_url']
            statuses_url = pull_json['statuses_url']
            review_url = pull_json['url'] + '/reviews'
            html_url = pull_json['html_url']
            labels = pull_json['labels']
            title = pull_json['title']
            rebaseable = self.acrn_url_info(num_url)['rebaseable']
            #self.update_statuses(statuses_url,head)
            if  base=='apl_sdc_stable':
                Coding_Guidelines=True
                label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","CI: apl_sdc_stable")
                label_message = "add branch_label sueecss" if label_status == 200 else "add branch_label fail"
                print(label_message)
            if self.CheckEmail(num, commits_url):
                Email_FLAG=True
                delete_email_flag=True
            else:
                Email_FLAG=False
                label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","no Signed-off-by")
                label_message = "add no Signed-off-by success" if label_status == 200 else "add no Signed-off-by success"
                print(label_message)
            if self.determine_doc(num):
                print(str(num)+":it is not a doc commit")
                check_json = self.acrn_url_info(statuses_url)
                for misra in check_json:
                    if misra['context'] == 'MISRA-C_Check':
                        is_MISRA=True
                        if misra['state'] == 'success':
                            Misra_Flag=True
                            label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/CI: no coding guideline")
                            label_message = "delete CI: no coding guideline success" if label_status == 200 else "delete CI: no coding guideline fail"
                            print(label_message)
                        elif misra['state'] == 'failure':
                            Misra_Flag=False
                        break
                for label in labels:
                    if label['name'] == 'CI: Tracked On Pass':
                        CI_FLAG=True
                    if label['name'] == 'Coding Guidelines: PASS' or 'kernel' in self.base_url:
                        Coding_Guidelines=True
                        if Misra_Flag==False:
                            self.update_statuses(statuses_url,"success","Pass","MISRA-C_Check")
                    if label['name'] == 'Automerge: Pass':
                        Automerge=True
                    if label['name'] == 'CI: Tracked On error':
                        Tracked_On_error=True
                    if label['name'] == 'status: on hold':
                        Status_on_hold=True
                    if label['name'] == 'CI: pending approve':
                        Pending_approve=True
                    if label['name'] == 'no Signed-off-by' and delete_email_flag:
                        label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/no Signed-off-by")
                        label_message = "delete no Signed-off-by success" if label_status == 200 else "delete no Signed-off-by fail"
                        print(label_message)
                if  Tracked_On_error==True and CI_FLAG==True: 
                    label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/CI: Tracked On Pass")
                    label_message = "delete CI: Tracked On Pass success" if label_status == 200 else "delete CI: Tracked On Pass fail"
                    print(label_message)
                    label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/CI: Tracked On error")
                    label_message = "delete CI: Tracked On error success" if label_status == 200 else "delete CI: Tracked On error fail"
                    print(label_message)                        
                    CI_FLAG=False 
                    Tracked_On_error=False
                if  CI_FLAG==False:
                    if self.TrackenOn(num, commits_url, html_url):
                        trackon_dict[num] = num_url
                        self.update_statuses(statuses_url,"success","Pass","Tracked-On/JIRA_GIT_ISSUE_Check")
                        label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","CI: Tracked On Pass")
                        label_message = "add CI: Tracked On Pass success" if label_status == 200 else "add CI: Tracked On Pass fail"
                        print(label_message)
                        CI_FLAG=True
                        if Tracked_On_error==True:
                            label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/CI: Tracked On error")
                            label_message = "delete CI: Tracked On error success" if label_status == 200 else "delete CI: Tracked On error fail"
                            print(label_message)
                    else:
                        self.update_statuses(statuses_url,"failure","Fail","Tracked-On/JIRA_GIT_ISSUE_Check")
                        label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","CI: Tracked On error")
                        label_message = "add CI: Tracked On error success" if label_status == 200 else "add CI: Tracked On error fail"
                        print(label_message) 
                if  Coding_Guidelines==False:
                    commits_json=self.acrn_url_info(comment_url)
                    for commit in commits_json:
                        commit_body=commit['body']
                        CI_CHECK1=re.findall(r'.*?No new violations to the coding guideline detected.*?', commit_body)
                        CI_CHECK2=re.findall(r'.*?No New Function Declaration/Definition Mismatch.*?', commit_body)
                        CI_CHECK3=re.findall(r'.*?No New Name Conflict.*?', commit_body)
                        if CI_CHECK1 and CI_CHECK2 and CI_CHECK3:
                            print("Coding_Guidelines == true")
                            label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/CI: no coding guideline")
                            label_message = "delete CI: no coding guideline success" if label_status == 200 else "delete CI: no coding guideline fail"
                            print(label_message)
                            Coding_Guidelines=True
                            if Misra_Flag==False:
                                self.update_statuses(statuses_url,"success","Pass","MISRA-C_Check")
                review_json = self.acrn_url_info(review_url)
                for review in review_json:
                    user = review["user"]["login"]
                    user_type = self.CheckUerType(user,num,statuses_url)                   
                    if review.get('state') == "CHANGES_REQUESTED" and user_type:
                        Approved_Flag=False
                    if review.get('state') == "APPROVED" and user_type:
                        Approved_Flag=True
                        print("Approved_Flag is true")
                        if Pending_approve==True:
                            label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/CI: pending approve")
                            label_message = "delete CI: pending approve success" if label_status == 200 else "delete CI: pending approve fail"
                            print(label_message)
                        break
                for statuess_json in check_json:
                    if statuess_json['context'] == 'default':
                        if statuess_json['state'] == 'success':
                            PremergeTest_Flag=True
                            print("PremergeTest_Flag pass")
                        break
                if Coding_Guidelines==False and 'hypervisor' in self.base_url and is_MISRA==False:
                    self.update_statuses(statuses_url,"failure","Fail","MISRA-C_Check")
                    label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","CI: no coding guideline")
                    label_message = "add CI: no coding guideline success" if label_status == 200 else "add CI: no coding guideline fail"
                    print(label_message)
                if Approved_Flag==True and PremergeTest_Flag==True:
                    CHECK_FLAG=True
                    if CI_FLAG==True and Coding_Guidelines==True:
                        merge_num_dict[num] = [0, comment_url, html_url]                   
                if CI_FLAG==True and Coding_Guidelines==True and CHECK_FLAG==True and Status_on_hold==False and Email_FLAG==True and rebaseable==True:
                    label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","Automerge: Pass")
                    label_message = "add automerge_label success" if label_status == 200 else "add automerge_label fail"
                    print(label_message)
                else:
                    if Approved_Flag==False and PremergeTest_Flag==True and CI_FLAG==True and Coding_Guidelines==True:
                        label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","CI: pending approve")
                        label_message = "add CI: pending approve success" if label_status == 200 else "add CI: pending approve fail"
                        print(label_message)
                    if CI_FLAG==False:
                        print("Tracked On is error")
                    if Coding_Guidelines==False:
                        print("ldra check is error")
                    if CHECK_FLAG==False:
                        print("three check is wrong")
                    if Automerge==True:
                        label_status=self.del_label(self.base_url+"/issues/"+str(num)+"/labels/Automerge: Pass")
                        label_message = "delete automerge_label success" if label_status == 200 else "delete automerge_label fail"
                        print(label_message)
                    continue
            else:
                print(str(num)+":it is a doc commit")
                label_status=self.add_label(self.base_url+"/issues/"+str(num)+"/labels","area: documentation")
                label_message = "新增doc_label成功" if label_status == 200 else "新增doc_label失败"
                print(label_message)
                continue

        merge_num_list = sorted(merge_num_dict.keys())
        read_num_list = sorted(read_num_dict.keys())
        
        ok_merge = list(set(merge_num_list) & set(sorted(trackon_dict.keys())))
        ok_merge_dict = {x: y[2] for x, y in merge_num_dict.items() if x in ok_merge}
        ok_merge_num_dict = {x: y for x, y in merge_num_dict.items() if x in ok_merge}
        logging.info('ok_merge_list %s' % ok_merge)
        logging.info('read_num_list %s' % read_num_list)
        if not operator.eq(read_num_list, merge_num_list):
            # 使用operator判断两个列表是否相同
            logging.info("可以rebase编号：%s" % ok_merge)
            # 发送邮件：可以merge的PR列表
            subject = 'Need merge PRs'
            content = 'PR can merge list:\n%s' % (
                json.dumps(ok_merge_dict))
            if ok_merge_dict:
                self.send_email(subject, content)
            for num, me_list in ok_merge_num_dict.items():
                if num in read_num_list:
                    ok_merge_num_dict[num][0] = 1
                    me_list[0] = 1
                if me_list[0] == 0:
                    #status_code = self.post_comments(me_list[1])
                    ok_merge_num_dict[num][0] = 1
                    #body = "修改成功" if status_code == 201 else "修改失败"
                    #logging.info(body)
            if ok_merge_num_dict:
                self.write_file(ok_merge_num_dict)


if __name__ == '__main__':
    url = ['https://api.github.com/repos/projectacrn/acrn-hypervisor',
           'https://api.github.com/repos/projectacrn/acrn-kernel']
    projectacrn_pullrequest = ProjectacrnPullRequest('acrnsi', '33385712d1129cc19d85d63b885fc152815fab94')
    #projectacrn_pullrequest = ProjectacrnPullRequest('ClaudZhang1995', 'zhangyun1995')
    for base_rul in url:
        projectacrn_pullrequest.base_url = base_rul
        projectacrn_pullrequest.projectcarn_merge_rebase()


#Tracked-On/JIRA_GIT_ISSUE_Check:

