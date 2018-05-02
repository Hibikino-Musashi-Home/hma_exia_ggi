#!/usr/bin/env python
# -*- coding: utf-8 -*-


#==================================================
#Go Get It 用ステートマシンのROSノード
#
#author: Yuma YOSHIMOTO
#==================================================


import sys
import os
import roslib
from common_pkg.srv import *

import nltk

sys.path.append(roslib.packages.get_pkg_dir('common_pkg') + '/script/common')
from common_import import *
from common_function import CommonFunction

sys.path.append(roslib.packages.get_pkg_dir('yoshimoto_pkg') + '/scripts')
from speech import Speech

rospy.sleep(5) #他のROSノードが立ち上がるまで待つ


#==================================================
#パラメータ
#==================================================
GP_LOOP_RATE = 30


#==================================================
#グローバル
#==================================================
cf = CommonFunction()
_speech=[]

object_id = 0
place_list = []
object_list = []

#==================================================
#Double Metaphoneのクライアント
#==================================================
def double_metaphone_client(f_name, i_text, a_distance) :
    rospy.wait_for_service('double_metaphone')
    try :
  		double_metaphone = rospy.ServiceProxy('double_metaphone', DoubleMetaphone)
  		resp = double_metaphone(f_name, i_text, a_distance)

  		return resp

    except rospy.ServiceException, e :
        print "Service call failed: %s"%e

#==================================================
#
#==================================================
class Init(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()
        
        cf.dbg_step_out()
        return 'exit1'


#==================================================
#
#==================================================
class WaitStartSig(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()

        raw_input('#####Type enter key to start#####')

        cf.dbg_step_out()
        return 'exit1'


#==================================================
#
#==================================================
class WaitFollowSig(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1', 'exit2'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()


        # 「Follow Me」と言われるまで待機
        dummy = _speech.ctrl_sync_rec(0.5)
        while not rospy.is_shutdown() :
          _speech.ctrl_sync_syn('Please tell me.! follow me.!')
          text = _speech.ctrl_sync_rec( 5)

          # Double Metaphoneにより単語リスト内の言葉に変換
          text_ = ""
          try :
            if text :
              while True :
                double_metaphone_ = double_metaphone_client("ggi/ggi_command_list", text[0]["TEXT"], 3)
                text_ = double_metaphone_.output_text
                #_speech.ctrl_sync_syn('The distance between ' + input_text_ + ' and ' + input_text[0]["TEXT"] + ' is ' + str(double_metaphone_.leven_distance))

                if text_ == "ERROR" :
                  _speech.ctrl_sync_syn('Please say again.')
                  text = _speech.ctrl_sync_rec( 5)

                else :
                  print text_
                  break

          except :
            print(sys.exc_info())

          try :
            if 'follow me' == text_ : # in text[0]["TEXT"]:
              _speech.ctrl_sync_syn('OK, I follow you.')
              break
          except :
            pass

        # 初期ポジションを記録
        try :
            init_pos = cf.get_tf('/map', '/base_link')
            rospy.set_param('/sm_ggi/p/init_pos/x', init_pos['x'])
            rospy.set_param('/sm_ggi/p/init_pos/y', init_pos['y'])
            rospy.set_param('/sm_ggi/p/init_pos/yaw', init_pos['yaw'])
            keyword_and_place = []
            keyword_and_place.append([{'id':0,'keyword': 'operator_position', 'pos':{'x': init_pos['x'], 'y': init_pos['y'], 'yaw': init_pos['yaw']}}])
            rospy.set_param('/sm_ggi/keyword_and_place_db', keyword_and_place)
        except :
            voice_text = "Error! Acquisition of initial position failed."
            _speech.ctrl_sync_syn( voice_text)

        cf.dbg_step_out()
        return 'exit1'

#==================================================
#
#==================================================
class FollowOperator(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1', 'exit2'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()

        if cf.dbg_srlc_mode() == 0:

            cf.ctrl_cam_pan_tilt(0.000, 0.000)

            #cf.ctrl_base_vel_abs(0.2, 0, 0)        
            p_0 = Popen(['rosrun', 'common_pkg', 'follow'], stdout=PIPE, stderr=PIPE)
            rospy.sleep(1)
            _speech.ctrl_sync_syn('Please start walking.!')
            rospy.sleep(1)

            while not rospy.is_shutdown():
                p_1 = Popen(['rosrun', 'common_pkg', 'wait_wsa.py', 'stop', '5'], stdout=PIPE, stderr=PIPE)
                rr,_,_ = select.select([p_0.stdout, p_0.stderr, p_1.stdout, p_1.stderr], [], [])
                if p_0.stdout in rr or p_0.stderr in rr:
                    if p_0.wait() == 1:
                        call(['rosnode', 'kill', '/wait_wsa'])
                        _speech.ctrl_sync_syn('I lost you! Please come back!')
                        cf.dbg_step_out()
                        return 'exit2'
                if p_1.stdout in rr or p_1.stderr in rr:
                    if p_1.wait() == 1:
                        _speech.ctrl_sync_syn('I recognize stop!')
                        cf.ctrl_cam_pan_tilt(0.000, 0.000)
                        break
                    else:
                        continue

            call(['rosnode', 'kill', '/follow'])
            cf.ctrl_base_vel_abs(0, 0, 0)
            rospy.sleep(0.1)
            cf.ctrl_base_vel_abs(0, 0, 0)
            # _speech.ctrl_sync_syn('I understood.!')
        
        cf.dbg_step_out()
        return 'exit1'

#==================================================
#
#==================================================
class LearnKeywords(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1', 'exit2'])

    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()

        global object_id
        global place_list
        global object_list

        try :
          while not rospy.is_shutdown():
            _speech.ctrl_sync_syn('Please say command.')
            input_text = _speech.ctrl_sync_rec( 5)

            # Double Metaphoneにより単語リスト内の言葉に変換
            input_text_ = ""
            try :
              if input_text :
                while True :
                  double_metaphone_ = double_metaphone_client("ggi/ggi_command_list", input_text[0]["TEXT"], 4)
                  input_text_ = double_metaphone_.output_text
                  #_speech.ctrl_sync_syn('The distance between ' + input_text_ + ' and ' + input_text[0]["TEXT"] + ' is ' + str(double_metaphone_.leven_distance))

                  if input_text_ == "ERROR" :
                    #_speech.ctrl_sync_syn('Sorry, I could not catch your command. Please say again.')
                    _speech.ctrl_sync_syn('Sorry, please say again.')
                    input_text = _speech.ctrl_sync_rec( 5)

                  else :
                    print input_text_
                    break

            except :
              print(sys.exc_info())

            try :
              # end training：キーワードを全部入れ終えた
              if 'complete training' == input_text_ : # in [text["TEXT"] for text in input_text]:
                _speech.ctrl_sync_syn('OK! I have finished the training phase!')

                # キーワードをファイルに出力
                try :
                  fp = open(os.path.expanduser('~') + '/ros_ws/hma/hma_ws_1/src/common_pkg/script/double_metaphone/command_list/ggi/ggi_place_list.txt', 'w')
                  fo = open(os.path.expanduser('~') + '/ros_ws/hma/hma_ws_1/src/common_pkg/script/double_metaphone/command_list/ggi/ggi_object_list.txt', 'w')
                  for place_ in place_list :
                    fp.write(str(place_) + '\n')
                  for object_ in object_list :
                    fo.write(str(object_) + '\n')
                  fp.close()
                  fo.close()

                except :
                  print(sys.exc_info())

                return 'exit1'

              # follow me：追従を再開する
              if  'follow me' == input_text_ : # in input_text[0]["TEXT"]:
                _speech.ctrl_sync_syn('OK! I will resume "follow me".')
                return 'exit2'

              # 新 learning keywords：キーワードを覚える
              if  'training keywords' == input_text_ :  # in input_text[0]["TEXT"]:
                phase_flag = 'place'
                pictuire_file_name = ''

                try :
                  object_id += 1
                except :
                  object_id = 0

                _speech.ctrl_sync_syn('OK! Please tell me information of this place')
                while not rospy.is_shutdown():
                  input_text = _speech.ctrl_sync_rec( 5)
                  try :
                    input_text = input_text[0]['TEXT']
                  except :
                    if phase_flag is 'place' :
                      _speech.ctrl_sync_syn('Please say again.')
                    elif phase_flag is 'object' :
                      _speech.ctrl_sync_syn('Please say again.')
                    continue

                  # Double Metaphoneにより単語リスト内の言葉に変換
                  input_text_ = ""
                  if input_text :
                    double_metaphone_ = double_metaphone_client("ggi/ggi_training_command_list", input_text, 1)
                    input_text_ = double_metaphone_.output_text

                  if 'stop' == input_text_ :# in input_text : # キーワードを覚えるモード，終了
                    if phase_flag is 'place' :
                      _speech.ctrl_sync_syn('OK! I memorized.')
                      _speech.ctrl_sync_syn('Next, Please tell me feature of this object')
                      phase_flag = 'object'

                    # 写真を撮る
                    elif phase_flag is 'object' :
                      #_speech.ctrl_sync_syn('OK! I will remember the object. Please show me the object.')
                      _speech.ctrl_sync_syn('OK! Please show me the object.')

                      rospy.sleep(0.25)
                      try :
                        _speech.ctrl_sync_syn('three, two, one')
                        pictuire_file_path = os.path.expanduser('~') + "/athome_outputdata/GoGetIt/" + pictuire_file_name + ".jpg"
                        #call(["rosrun", "ggi_pkg", "img_save.py", "/camera/rgb/image_rect_color", pictuire_file_path])
                      except :
                        _speech.ctrl_sync_syn("I can't take the photo.")
                      break

                  elif 'not correct' == input_text_ or 'not the correct' == input_text_:# in input_text : # 直前のキーワードを削除
                    try :
                      keyword_and_place_db = rospy.get_param('/sm_ggi/keyword_and_place_db')
                      keyword_and_place_db.pop()
                      rospy.set_param('/sm_ggi/keyword_and_place_db', keyword_and_place_db)
                      _speech.ctrl_sync_syn('OK.')
                      if phase_flag is 'place' :
                        place_list.pop()
                        _speech.ctrl_sync_syn('Please say again')
                      elif phase_flag is 'object' :
                        object_list.pop()
                        _speech.ctrl_sync_syn('Please say again')
                    except :
                      pass

                  else :# 新しいキーワード
                    # _speech.ctrl_sync_syn( input_text)
                    pictuire_file_name = pictuire_file_name + '_' + input_text
                    # 座標の取得
                    pos = cf.get_tf('/map', '/base_link')
                    # キーワードの保存
                    try :
                      keyword_and_place_db = rospy.get_param('/sm_ggi/keyword_and_place_db')
                    except :
                      
                      keyword_and_place_db = []
                    keyword_and_place_db.append([{'id': object_id, 'keyword': input_text, 'pos':{'x': pos['x'], 'y': pos['y'], 'yaw': pos['yaw']}}])
                    rospy.set_param('/sm_ggi/keyword_and_place_db', keyword_and_place_db)

                    if phase_flag is 'place' :         
                      try :           
                        place_list.append(input_text)
                      except :
                        place_list = []
                        place_list.append(input_text)

                    elif phase_flag is 'object' :   
                      try :          
                        object_list.append(input_text)
                      except :
                        object_list = []
                        object_list.append(input_text)
  
            except :
              # キーワード or follow me or complete training タイムアウト．ループで再度尋ねる
              #_speech.ctrl_sync_syn('ERROR! I found an error in "Learn keywords state".')
              pass

        except :
          _speech.ctrl_sync_syn('ERROR! I found an error in "Learn keywords state".')
        cf.dbg_step_out()

        return 'exit1'

#==================================================
#
#==================================================
class BackToOperatorPoint(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()
        try :
          try :
            _speech.ctrl_sync_syn('I will move to the start point.')
            pos   = rospy.get_param('/common_param/p/db/ggi/test_phase_start_pos')
            pos_x   = pos["x"]
            pos_y   = pos["y"]
            pos_yaw = pos["yaw"]
          except :
            _speech.ctrl_sync_syn('ERROR! I do not remember the starting point.')
            pos_x   = 0.0
            pos_y   = 0.0
            pos_yaw = 0.0
          try :
            #rospy.set_param('/ctrl_base_slam_nav_go_to_node/p/pos/x',   pos_x)
            #rospy.set_param('/ctrl_base_slam_nav_go_to_node/p/pos/y',   pos_y)
            #rospy.set_param('/ctrl_base_slam_nav_go_to_node/p/pos/yaw', pos_yaw)
            #call(['rosrun','gpsr_pkg','ctrl_base_slam_nav_go_to_node.py'])
            cf.ctrl_base_slam_nav_go_to_silent(pos_x, pos_y, pos_yaw)
            _speech.ctrl_sync_syn("I arrived at the start point.")
          except :
            _speech.ctrl_sync_syn('ERROR! I can not move to the start point.')
        except :
          _speech.ctrl_sync_syn('ERROR! I found an error in "Back To Operator Point State".')
        cf.dbg_step_out()
        return 'exit1'


#==================================================
#
#==================================================
class WaitTestPhaseStartSig(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()

        # 「Start」と言われるまで待機
        dummy = _speech.ctrl_sync_rec(1)
        _speech.ctrl_sync_syn('I am ready to start the test phase.')
        while not rospy.is_shutdown():
          _speech.ctrl_sync_syn('The operator says to me "start".')
          texts = _speech.ctrl_sync_rec(5)
          try :
            if 'start' in [text["TEXT"] for text in texts]:
              _speech.ctrl_sync_syn('I recognized your command.')
              break
          except :
            pass

        cf.dbg_step_out()
        return 'exit1'


#==================================================
#
#==================================================
class UnderstandCommand(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()

        try :
          #go_place = ""
          #bring_object = ""
          _speech.ctrl_sync_syn('Operater! Please say your commands after the beep!')
          while not rospy.is_shutdown():

            # コマンドの取得
            try :
              cmd_text = _speech.ctrl_sync_rec(5)[0]["TEXT"]
              print "---------------------"
              print cmd_text
              print "---------------------"

              if cmd_text :
                _speech.ctrl_sync_syn("OK! Please wait.")
                # 品詞分け：名詞，副詞，数字だけ抽出
                try :
                  cmd_token = nltk.word_tokenize(cmd_text)
                  cmd_token_list = nltk.pos_tag(cmd_token)
                  place_and_object_inf_list = []
                  before_flag = False
                  print cmd_token_list
                  for word, part in cmd_token_list :
                    if part == 'NN' or part == 'JJ' or part == 'CD' or part == 'NNS' or part == 'NNP' or part == 'NNPS' or part == 'POS' :
                      if before_flag :
                        place_and_object_inf_list.pop()
                        place_and_object_inf_list.append(before_word + ' ' + word)
                        before_word = before_word + ' ' + word
                      else :
                        place_and_object_inf_list.append(word)
                        before_word = word
                    
                      before_flag = True
                      
                    else :
                      before_flag = False

                except :
                  print(sys.exc_info())
                print place_and_object_inf_list
                    
                # double metaphoneを使ってplaceとobject情報を抽出
                try :
                  go_place = ''
                  bring_object = ''
                  min_distance_place = 10
                  min_distance_object = 10
                  for word in place_and_object_inf_list :
                    dmeta_place = double_metaphone_client('ggi/ggi_place_list', word, 2)
                    dmeta_object = double_metaphone_client('ggi/ggi_object_list', word, 2)
                    
                    print dmeta_place
                    print "----------------"
                    print dmeta_object

                    if dmeta_place != 'ERROR' or dmeta_object != 'ERROR' :
                      if dmeta_place.leven_distance <= dmeta_object.leven_distance :
                        if min_distance_place > dmeta_place.leven_distance :
                          go_place = dmeta_place.output_text
                          min_distance_place = dmeta_place.leven_distance
                      else :
                        if min_distance_object > dmeta_object.leven_distance :
                          bring_object = dmeta_object.output_text
                          min_distance_object = dmeta_object.leven_distance
                    else :
                      _speech.ctrl_sync_syn("I'm sorry. Please say again after the beep")

                except :
                  print(sys.exc_info())
                
            except :
              _speech.ctrl_sync_syn("I'm sorry. Please say again after the beep")
              continue

            print go_place, bring_object
            if go_place != 'ERROR' and bring_object != 'ERROR' :
              if go_place != '' and bring_object != '' :
                # コマンドが合っているか確認
                while not rospy.is_shutdown() :
                  # 文章に変換する場合ここに記述
                  if go_place == 'person' :
                    go_place = 'near the person'

                  _speech.ctrl_sync_syn("I will go " + go_place + " and bring a " + bring_object + " to you.")

                  #_speech.ctrl_sync_syn("Is it OK to execute this command? Please say! Yes! or No! after the beep")
                  _speech.ctrl_sync_syn("Is it OK ? Yes! or No! after the beep ")
                  texts = _speech.ctrl_sync_rec(5)
                  try :
                    if  'yes' in texts[0]["TEXT"] :
                    #if any(s.endwith('yes') for s in texts) :
                    #if  'yes' in [text["TEXT"] for text in texts]:
                      _speech.ctrl_sync_syn('OK! I understood your command! I try it.')
                      rospy.set_param('/sm_ggi/command/place', go_place) # 命令コマンドを記録
                      rospy.set_param('/sm_ggi/command/object', bring_object)
                      return 'exit1'
                    elif  'no' in texts[0]["TEXT"] :
                    #elif any(s.endwith('no') for s in texts) :
                    #elif 'no' in [text["TEXT"] for text in texts] :
                      _speech.ctrl_sync_syn("I'm sorry. Please say again after the beep")
                      break
                  except :
                    pass
              else :
                _speech.ctrl_sync_syn("I'm sorry. Please say again after the beep")                
            else :
              _speech.ctrl_sync_syn("I'm sorry. Please say again after the beep")

        except :
          _speech.ctrl_sync_syn('ERROR! I found an error in "Understand Command State".')
          print(sys.exc_info())

        cf.dbg_step_out()
        return 'exit1'


#==================================================
#
#==================================================
class MakeCommandSet(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])

    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()

        try :
          # キーワードデータベースを取得
          keyword_and_place_db = []
          try :
            keyword_and_place_db = rospy.get_param('/sm_ggi/keyword_and_place_db')
          except :
            _speech.ctrl_sync_syn('ERROR! The database is empty.')

          # コマンド内容から実行コードを生成する
          cmd_text    = []
          command_set = []
          try :
            cmd_place = rospy.get_param('/sm_ggi/command/place')
            cmd_object = rospy.get_param('/sm_ggi/command/object')
            print cmd_place, cmd_object
          except :
            _speech.ctrl_sync_syn('ERROR! I could not get the command_text.')

          """
          # 命令文にキーワードが含まれているか判定
          for keyword_and_place in keyword_and_place_db :
            print(keyword_and_place[0]['keyword'])
            text_find = cmd_text.find(keyword_and_place[0]['keyword'])
            if text_find > -1 :
                command_set.append([text_find,keyword_and_place])
            else :
                pass
          command_set = sorted(command_set)
          print(command_set)
          rospy.set_param('/sm_ggi/command_set', command_set)
          """

          id_box = [0 for i in range(5)] #range(object_id)  # 投票ボックス作成
          try :
            for keyword_and_place in keyword_and_place_db :
              print keyword_and_place
              if cmd_place        == keyword_and_place[0]['keyword'] :
                place_id          = keyword_and_place[0]['id']
                id_box[ int(place_id) - 1] = id_box[ int(place_id - 1)] + 1  # Place 投票
              elif cmd_object     == keyword_and_place[0]['keyword'] :
                obj_id            = keyword_and_place[0]['id']
                id_box[   int(obj_id) - 1] = id_box[   int(obj_id - 1)] + 1  # Object 投票
              print id_box

              #try :
              #  print place_id, obj_id
              #  if place_id == obj_id :
              #    rospy.set_param('/sm_ggi/go_pos', keyword_and_place[0]['pos'])
              #except :
              #  continue
          except :
            print(sys.exc_info())            
          print("==========================")
          print id_box, id_box.index(max(id_box))
          # 一番投票数が多いIDを抽出
          try :
            for keyword_and_place in keyword_and_place_db :
              try :
                if id_box.index(max(id_box)) + 1 == int(keyword_and_place[0]['id']) :
                  rospy.set_param('/sm_ggi/go_pos', keyword_and_place[0]['pos'])
              except :
                pass
          except :
            print(sys.exc_info()) 

        except :
          _speech.ctrl_sync_syn('ERROR! I found an error in "Make Command List State".')

        cf.dbg_step_out()
        return 'exit1'

#==================================================
#
#==================================================
class ProcCommandSet(smach.State):
    #==================================================
    #コンストラクタ
    #==================================================
    def __init__(self):
        smach.State.__init__(self, outcomes=['exit1'])


    #==================================================
    #実行関数
    #==================================================
    def execute(self, userdata):
        cf.dbg_step_in()
        try :
          # キーワードデータベースを取得
          command_set = []
          try :
            # command_set = rospy.get_param('/sm_ggi/command_set')
            go_pos = rospy.get_param('/sm_ggi/go_pos')
          except :
            _speech.ctrl_sync_syn('ERROR! The command_set is empty.')

          # コマンドの処理
          try :
            """
            # 命令を実行する
            for command in command_set :
              _speech.ctrl_sync_syn("I go to " + command[1][0]["keyword"])
              #rospy.set_param('/ctrl_base_slam_nav_go_to_node/p/pos/x',   command[1][0]["pos"]['x'])
              #rospy.set_param('/ctrl_base_slam_nav_go_to_node/p/pos/y',   command[1][0]["pos"]['y'])
              #rospy.set_param('/ctrl_base_slam_nav_go_to_node/p/pos/yaw', command[1][0]["pos"]['yaw'])
              #call(['rosrun','gpsr_pkg','ctrl_base_slam_nav_go_to_node.py'])
              cf.ctrl_base_slam_nav_go_to_silent( command[1][0]["pos"]['x'], command[1][0]["pos"]['y'], command[1][0]["pos"]['yaw'])
              _speech.ctrl_sync_syn("I arrived at "+command[1][0]["keyword"])
            """
            print go_pos
            cf.ctrl_base_slam_nav_go_to_silent(go_pos['x'], go_pos['y'], go_pos['yaw'])
            _speech.ctrl_sync_syn( "I arrived.")
            
          except :
            print(sys.exc_info())
            _speech.ctrl_sync_syn( "Error! I can not move.")

        except :
          _speech.ctrl_sync_syn('ERROR! I found an error in "Process Command List State".')
        cf.dbg_step_out()
        return 'exit1'

#==================================================
#メイン関数
#==================================================
if __name__ == '__main__':
    rospy.init_node(os.path.basename(__file__).split('.')[0])

    rospy.loginfo('[' + rospy.get_name() + ']: Task Go Get It start')
    rospy.loginfo('[' + rospy.get_name() + ']: Please input first start name')
    _speech = Speech()
    start_state = raw_input('>> ')
    if not start_state:
        start_state = 'WaitStartSig'

    rospy.loginfo('[' + rospy.get_name() + ']: Start state machine')

    #--------------------------------------------------
    #ステートマシンの宣言
    #--------------------------------------------------
    sm = smach.StateMachine(outcomes=['exit'])

    with sm:
        smach.StateMachine.add('Init',                  Init(),                  transitions={'exit1':start_state})
        smach.StateMachine.add('WaitStartSig',          WaitStartSig(),          transitions={'exit1':'WaitFollowSig'})
        smach.StateMachine.add('WaitFollowSig',         WaitFollowSig(),         transitions={'exit1':'FollowOperator',     'exit2':'WaitFollowSig'})
        smach.StateMachine.add('FollowOperator',        FollowOperator(),        transitions={'exit1':'LearnKeywords',      'exit2':'FollowOperator'})
#        smach.StateMachine.add('LearnKeywords',         LearnKeywords(),         transitions={'exit1':'BackToOperatorPoint','exit2':'FollowOperator'})
        smach.StateMachine.add('LearnKeywords',         LearnKeywords(),         transitions={'exit1':'UnderstandCommand','exit2':'FollowOperator'})
        smach.StateMachine.add('BackToOperatorPoint',   BackToOperatorPoint(),   transitions={'exit1':'UnderstandCommand'})
#        smach.StateMachine.add('BackToOperatorPoint',   BackToOperatorPoint(),   transitions={'exit1':'WaitTestPhaseStartSig'})
        smach.StateMachine.add('WaitTestPhaseStartSig', WaitTestPhaseStartSig(), transitions={'exit1':'UnderstandCommand'})
        smach.StateMachine.add('UnderstandCommand',     UnderstandCommand(),     transitions={'exit1':'MakeCommandSet'})
        smach.StateMachine.add('MakeCommandSet',        MakeCommandSet(),        transitions={'exit1':'ProcCommandSet'})
        smach.StateMachine.add('ProcCommandSet',        ProcCommandSet(),        transitions={'exit1':'BackToOperatorPoint'})

    sis = smach_ros.IntrospectionServer('sm', sm, '/SM_ROOT')
    sis.start()

    outcome = sm.execute()
