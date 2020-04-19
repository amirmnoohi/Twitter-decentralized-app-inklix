import hashlib
import os
import os.path
from base64 import b64encode, b64decode
from binascii import hexlify
from datetime import datetime

import bcrypt
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import torndb
from Crypto.PublicKey import RSA
from tornado.options import define, options

# ------------------------------------------------- for signing and public key & priv8 key
import functions

# -------------------------------------------------

define("port", default=1104, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1:3306", help="messenger database host")
define("mysql_database", default="blockchain", help="messenger database name")
define("mysql_user", default="root", help="messenger database user")
define("mysql_password", default="11041104", help="messenger database password")
profit = 0.2
ratio = 0.5
keysize = 1024


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            # GET METHOD :
            (r"/signup", Signup),
            (r"/login", Login),
            (r"/logout", Logout),
            (r"/getuserinfo", Getuserinfo),
            (r"/sendpost", SendPost),
            (r"/getpost", GetPost),
            (r"/likepost", LikePost),
            (r"/trustpost", TrustPost),
            (r"/fetchpool", FetchPool),
            (r"/fetchblockchain", FetchBlockchain),
            (r"/puttoblockchain", PutToBlockchain),
            (r"/updatevalopt", UpdateValueOpportunity),
            (r"/sendcomment", Defaulthandler),  # Not Done
            (r"/getcomment", Defaulthandler),  # Not Done
            # -----------------------------------------------------------------------
            (r"/test", Test),
            (r"/(favicon\.ico)", tornado.web.StaticFileHandler, {'path': ''}),
            (r".*", Defaulthandler),
        ]
        settings = dict()
        super(Application, self).__init__(handlers, **settings)
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def check_username(self, user):
        resuser = self.db.get("SELECT * from users where username = %s", user)
        if resuser:
            return True
        else:
            return False

    def get_hashed_password(self, plain_text_password):
        return bcrypt.hashpw(plain_text_password.encode('utf8'), bcrypt.gensalt())

    def check_hashed_password(self, plain_text_password, hashed_password):
        return bcrypt.checkpw(plain_text_password.encode('utf8'), hashed_password.encode('utf8'))

    def check_pass(self, username, password):
        resuser = self.db.get("SELECT * from users where username = %s", username)
        return self.check_hashed_password(password, resuser['password'])

    def opportunity(self, username):
        return self.db.get("""select val_opt from users where username = %s""", username)['val_opt']

    def check_loggedin(self, username, password):
        resuser = self.db.get("SELECT * from users where username = %s ", username)
        if resuser['is_active'] == 1:
            return True
        else:
            return False

    def check_date(self, dt):
        for zxc in dt:
            if not zxc.isdigit():
                return False
        return True

    def user_from_token(self, token):
        username = self.db.get("""
                    Select username
                    from users
                    where token = %s
                    """, token)
        if username:
            return username['username']
        else:
            return False

    def is_miner(self, username):
        user = self.db.get("Select role from users where username = %s", username)
        if user['role'] == 2:
            return True
        else:
            return False


class Defaulthandler(BaseHandler):
    def get(self):
        output = {'POWERED BY': 'AMIR M NOOHI'}
        self.write(output)

    def post(self, *args, **kwargs):
        output = {'POWERED BY': 'AMIR M NOOHI'}
        self.write(output)


class Signup(BaseHandler):
    def get(self, *args, **kwargs):
        if not self.check_username(self.get_argument('username')):
            public, private = functions.newkeys(1024)
            private = private.exportKey('PEM')
            public = public.exportKey('PEM')
            # generating public key and private key in ~/keys/username:
            directory = os.path.join(os.path.join(os.getcwd(), 'keys'), self.get_argument('username'))
            if not os.path.exists(directory):
                os.mkdir(directory)
            f = open(os.path.join(directory, 'public_key.PEM'), 'w')
            f.write(public)
            f.close()
            f = open(os.path.join(directory, 'private_key.PEM'), 'w')
            f.write(private)
            f.close()
            # insert data to database:
            self.db.execute("""
                            INSERT INTO users (username, password, firstname, lastname,is_active, created_at,
                            updated_at , prev_req_at , val_opt) values (%s,%s,%s,%s,%s,NOW(),NOW(),NOW(),0)
                            """,
                            self.get_argument('username'),
                            self.get_hashed_password(self.get_argument('password')),
                            self.get_argument('firstname', default=None),
                            self.get_argument('lastname', default=None), '0',
                            )

            output = {'code': '200',
                      'message': 'Signed Up Successfully',
                      'public_key': public,
                      'private_key': private
                      }
            self.write(output)
        else:
            output = {'code': '204',
                      'message': 'User Exist Try Another!'}
            self.write(output)


class Login(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            if self.check_pass(self.get_argument('username'), self.get_argument('password')):
                if not self.check_loggedin(self.get_argument('username'), self.get_argument('password')):
                    token = str(hexlify(os.urandom(16)))
                    self.db.execute("""
                                    UPDATE users
                                    SET token = %s , is_active = 1 , updated_at = %s
                                    WHERE username = %s
                                    """, token, datetime.now(), self.get_argument('username'))
                    output = {
                        'code': '200',
                        'message': 'Logged in Successfully',
                        'token': token
                    }
                    self.write(output)
                else:
                    output = {'code': '220',
                              'message': 'You are already logged in!'}
                    self.write(output)
            else:
                output = {'code': '401',
                          'message': 'Password is not Correct'}
                self.write(output)
        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


class Logout(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            if self.check_pass(self.get_argument('username'), self.get_argument('password')):
                if self.check_loggedin(self.get_argument('username'), self.get_argument('password')):
                    self.db.execute("""
                                    UPDATE users
                                    SET token = %s , is_active = 0 , updated_at = %s
                                    WHERE username = %s
                                    """, None, datetime.now(), self.get_argument('username'))
                    output = {
                        'code': '200',
                        'message': 'Logged Out Successfully',
                    }
                    self.write(output)
                else:
                    output = {'code': '200',
                              'message': 'You Have not Logged in Yet!'}
                    self.write(output)
            else:
                output = {'code': '401',
                          'message': 'Password is not Correct'}
                self.write(output)
        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


class SendPost(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            self.db.execute("""
                                        insert into posts (poster_username,post_title, post_text, post_image, comments, likes,
                                         trusts, updated_at,created_at)
                                        values (%s,%s,%s,%s,0,0,0,NOW(),NOW())
                                        """,
                            self.user_from_token(self.get_argument('token')),
                            self.get_argument('post_title'),
                            self.get_argument('text', default=None),
                            self.get_argument('image', default=None)
                            )

            output = {'code': '200',
                      'message': 'Post Sent Successfully'}
            self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class LikePost(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            self.db.execute("""
                                        UPDATE posts
                                        SET likes = likes +1
                                        where id = %s
                                        """,
                            self.get_argument('id')
                            )

            output = {'code': '200',
                      'message': 'Post Liked Successfully'}
            self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class TrustPost(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            trust_user = self.db.get("SELECT trust from users where username = %s",
                                     self.user_from_token(self.get_argument('token')))
            amount = (trust_user['trust'] * ratio / 100) + 0.005
            directory = os.path.join(os.path.join(os.getcwd(), 'keys'),
                                     self.user_from_token(self.get_argument('token')))
            private = open(os.path.join(directory, 'private_key.PEM'), 'r').read()
            private_key = RSA.importKey(private)
            message = {'trust_src': self.user_from_token(self.get_argument('token')),
                       'trust_dst': self.get_argument('id'), 'amount': amount}
            signature = b64encode(functions.sign(str(message), private_key))
            self.db.execute("""
                                        insert into trusts_pool (trust_src, trust_dst, amount, created_at,signature) 
                                        values (%s,%s,%s,NOW(),%s)
                                        """,
                            self.user_from_token(self.get_argument('token')),
                            self.get_argument('id'), amount, signature
                            )
            output = {'code': '200',
                      'message': 'Post Trusting Sent to Pool'}
            self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class FetchPool(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.is_miner(self.user_from_token(self.get_argument('token'))):
                if self.opportunity(self.user_from_token(self.get_argument('token'))):
                    res = self.db.query("""
                                    select id,trust_src,trust_dst,amount,signature,
                                    CAST(trusts_pool.created_at as char) as 'date' 
                                    from trusts_pool order by created_at asc """)
                    ans = {}
                    block_number = 0
                    for i in res:
                        ans['block ' + str(block_number)] = i
                        block_number += 1
                    ans['code'] = '200'
                    ans['message'] = 'Pool Fetched Successfully'
                    self.write(ans)
                else:
                    output = {'code': '300',
                              'message': 'You don\'t Have Opportunity'}
                    self.write(output)
            else:
                output = {'code': '404',
                          'message': 'You are not Miner'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class FetchBlockchain(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.is_miner(self.user_from_token(self.get_argument('token'))):

                res = self.db.query("""
                                select id,data,prev_hash,hash,CAST(blocks.created_at as char) as 'date' 
                                from blocks order by created_at asc """)
                ans = {}
                block_number = 0
                for i in res:
                    ans['bock ' + str(block_number)] = i
                    block_number += 1
                ans['code'] = '200'
                ans['message'] = 'Blockchain Fetched Successfully'
                self.write(ans)
            else:
                output = {'code': '404',
                          'message': 'You are not Miner'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class PutToBlockchain(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.is_miner(self.user_from_token(self.get_argument('token'))):
                miner = self.db.get("""select * from users where username = %s""",
                                    self.user_from_token(self.get_argument('token')))
                if miner['val_opt'] > 0:
                    data = self.db.get("""
                                            Select id,trust_src,trust_dst,amount,signature 
                                            from trusts_pool where id = %s""",
                                       self.get_argument('trust_pool_id'))
                    print(data)
                    if (data):
                        # check for signature :
                        message = dict()
                        message['trust_src'] = data['trust_src']
                        message['trust_dst'] = unicode(data['trust_dst'])
                        message['amount'] = data['amount']
                        directory = os.path.join(os.path.join(os.getcwd(), 'keys'), data['trust_src'])
                        public_key = RSA.importKey(open(os.path.join(directory, 'public_key.PEM'), 'r').read())
                        verify = functions.verify(str(message), b64decode(data['signature']), public_key)
                        if verify:
                            # creating block data for computing hash
                            last_id = self.db.get("""
                            select id from blocks order by id desc LIMIT 1""")
                            last_id = last_id['id'] + 1
                            alldata = {}
                            alldata['data'] = str(dict(data))
                            alldata['id'] = last_id
                            prev_hash = self.db.get("""
                            select prev_hash from blocks where id = %s""", self.get_argument('prev_block_id'))
                            if not prev_hash:
                                output = {'code': '404',
                                          'message': 'Prev Block Not Found'}
                                self.write(output)
                            prev_hash = prev_hash['prev_hash']
                            alldata['prev_hash'] = prev_hash
                            hash = hashlib.sha256(str(alldata)).hexdigest()
                            alldata['created_at'] = datetime.now()
                            alldata['hash'] = hash
                            self.db.execute("""
                            insert into blocks (data, prev_hash, hash, created_at) values (%s,%s,%s,%s)""",
                                            alldata['data'], alldata['prev_hash'], alldata['hash'],
                                            alldata['created_at'])
                            # delete trust record :
                            self.db.execute("""
                            delete from trusts_pool where id = %s""", self.get_argument('trust_pool_id'))
                            # increase trust of post :
                            self.db.execute("""
                            UPDATE posts
                            set trusts = trusts + %s
                            where id = %s""", data['amount'], data['trust_dst'])
                            # increase trust of user :
                            poster_username = self.db.get("""
                            select poster_username from posts where id = %s""", data['trust_dst'])
                            poster_username = poster_username['poster_username']
                            self.db.execute("""
                                            UPDATE users
                                            set trust = trust + %s
                                            where username = %s""", data['amount'] * profit, poster_username)
                            # reward miner with 5 * amount :
                            self.db.execute("""
                            update users
                            set trust = trust + %s , val_opt = val_opt - 1
                            where username = %s""", data['amount'] * 5,
                                            self.user_from_token(self.get_argument('token')))
                            # -------------------------------------------
                            output = {'code': '200',
                                      'message': 'Trust Put in Blockchain #' + str(last_id)}
                            self.write(output)
                        else:
                            # delete wrong record :
                            self.db.execute("""
                                                    delete from trusts_pool where id = %s""",
                                            self.get_argument('trust_pool_id'))
                            output = {'code': '800',
                                      'message': 'Can\'t Validate Signature'}
                            self.write(output)

                    else:
                        output = {'code': '404',
                                  'message': 'trust_pool_id Not Found'}
                        self.write(output)

                else:
                    output = {'code': '900',
                              'message': 'Not Enough Opportunity'}
                    self.write(output)

            else:
                output = {'code': '404',
                          'message': 'You are not Miner'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


# haji man chon truncate kardam ye error toye gharar dadan block mikhore
# bezar genesis block ro besazam
class GetPost(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            res = self.db.query(
                "select id,poster_username,post_title,post_text,post_image,comments,likes,trusts,"
                "CAST(posts.updated_at as CHAR) as 'updated_at' , CAST(posts.created_at as CHAR) as 'created_at'"
                " from posts where poster_username = %s",
                self.get_argument('username'))
            ans = {}
            block_number = 0
            for i in res:
                ans['block ' + str(block_number)] = i
                block_number += 1
            ans['message'] = str(block_number)
            ans['code'] = '200'
            self.write(ans)

        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


class UpdateValueOpportunity(BaseHandler):
    def get(self, *args, **kwargs):
        if self.user_from_token(self.get_argument('token')):
            if self.is_miner(self.user_from_token(self.get_argument('token'))):
                info = self.db.get("""select prev_req_at,val_opt,trust from users where username = %s""",
                                   self.user_from_token(self.get_argument('token')))
                diff_day = ((datetime.now() - info['prev_req_at']).total_seconds()) / 86400
                new_val_opt = diff_day * 10 * info['trust'] + info['val_opt']
                self.db.execute("""update users set val_opt = %s , prev_req_at = %s where username = %s""",
                                new_val_opt, datetime.now(), self.user_from_token(self.get_argument('token')))
                output = {'code': '200',
                          'message': 'Value Opportunity Update',
                          'new_val_opt': new_val_opt}
                self.write(output)
            else:
                output = {'code': '404',
                          'message': 'You are not Miner'}
                self.write(output)

        else:
            output = {'code': '401',
                      'message': 'Token is not Correct'}
            self.write(output)


class Getuserinfo(BaseHandler):
    def get(self, *args, **kwargs):
        if self.check_username(self.get_argument('username')):
            out = self.db.get("""
                            select username , firstname , lastname ,trust
                            from users
                            where username = %s 
                               """, self.get_argument('username'))
            output = {
                'code': '200',
                'message': 'User Was Found'}
            output['username'] = out['username']
            output['firstname'] = out['firstname']
            output['lastname'] = out['lastname']
            output['trust'] = out['trust']
            directory = os.path.join(os.path.join(os.getcwd(), 'keys'), self.get_argument('username'))
            output['public_ket'] = open(os.path.join(directory, 'public_key.PEM')).read()
            self.write(output)

        else:
            output = {'code': '404',
                      'message': 'User Not Found'}
            self.write(output)


# class Test(BaseHandler):
#     def get(self, *args, **kwargs):
#         # -- creating genesis block !
#         now_time = datetime.now()
#         self.db.execute("""
#         insert into blocks (data, prev_hash, hash, created_at) values (%s,%s,%s,%s)""", "Genesis Block", "1104",
#                         "47386f63486864fba95ee71e2b3f636fedd9577ea98b57d59e27c5effb68413a", now_time)
#         alldata = {'id': 1, 'data': "Genesis Block", 'prev_hash': "1104"}
#         hash = hashlib.sha256(str(alldata)).hexdigest()


class Test(BaseHandler):
    def get(self, *args, **kwargs):
        directory = os.path.join(os.path.join(os.getcwd(), 'keys'), self.get_argument('username'))
        print(directory)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
