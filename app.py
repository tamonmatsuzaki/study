from flask import Flask, render_template, request, redirect, flash, session
# htmlの画面に直接じゃなく、間接的に処理をするときはredirectを使う 
# flashはバリデーションのエラーメッセージを表示する際に用いる

import psycopg2
import psycopg2.extras
# バリデーションの所で使用。（re.match, resarch など）
import re
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

def get_connection(): 
    DB_HOST = 'localhost'
    DB_PORT = '5432'
    DB_NAME = 'postgres'
    DB_USER = 'postgres'
    DB_PASS = 'postgres'
    return psycopg2.connect(f'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

@app.route('/')
def index():
	return render_template('login.html')
    

@app.route('/create')
def create():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
            SELECT
                ken_code
                , ken_name
            FROM
                todoufuken
            """

            cur.execute(sql) 
            todoufuken_list = cur.fetchall()
            sql = """
            SELECT
                shikaku_code
                , shikaku_name 
            FROM
                shikaku
            """
            cur.execute(sql)
            shikaku_list = cur.fetchall()
            print(todoufuken_list)
            print(shikaku_list)

    if 'mail' not in session:
        return redirect('/')

    return render_template('create.html', todoufuken_list=todoufuken_list, shikaku_list=shikaku_list)

@app.post('/login')
def login():
    form = request.form
# メールアドレスからパスワード確認

    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
            SELECT
                mail,
                password,
                lock_flag,
                user_id
            FROM 
                users
            WHERE
                mail = %s
            """
            data = [
                form['mail']
            ]
            cur.execute(sql, data)
            user_login = cur.fetchall()

            print("かきく", type(user_login))
            print("はひふ", user_login)
            # print("あいう", user_login[0]['lock_flag'])
 

            is_error = False

            if form['mail'] == "":
                is_error = True
                flash('※ID（メールアドレス）を入力してください', 'ng_mail')
            if form['password'] == "":
                is_error =True
                flash('※パスワードを入力してください', 'ng_pass')

# ここからロックフラグの処理を開始
            if user_login == []:
                is_error = True
                flash('※正しいメールアドレスを入力してください', 'ng_mail')
            else:
                if int(user_login[0]['lock_flag']) == 3:
                    is_error = True
                    flash('※アカウントがロックされています', 'ng_pass')
                elif not check_password_hash(user_login[0]['password'], form['password']):
                    us_lock = int(user_login[0]['lock_flag']) + 1 
                    sql = """
                    UPDATE
                        users
                    SET
                        lock_flag = %s
                    WHERE
                        user_id = %s 
                    """
                    cur.execute(sql, [us_lock, user_login[0]['user_id']])
                    conn.commit()
                
                    is_error = True
                    flash('※正しいパスワードを入力してください', 'ng_pass')


            if is_error:
                return redirect('/')

            sql = """
            UPDATE
                users
            SET
                lock_flag = '0'
            WHERE
                user_id = %s 
            """
            cur.execute(sql, [user_login[0]['user_id']])
            conn.commit()
# セッションを書き込む。
            session['mail'] = form['mail']

    return redirect('/dashboard')


@app.route('/dashboard')
def dashboard():
# セッションを読み込み
    if 'mail' not in session:
        return redirect('/')
    
    return render_template('dashboard.html')

@app.route('/user_detail/<user_id>') #joinをして連結　性別、都道府県を出すように
def user_detail(user_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
# shikakuはsqlを別にする。
            sql = """
            SELECT 
                ur.user_id, 
                ur.name,
                ui.name_kana,
                ui.gender,
                ur.password,
                ur.mail,
                ui.yubin,
                ui.ken_code,
                ui.jyusyo,
                td.ken_name
            FROM 
                users AS ur
                JOIN 
                    user_info AS ui
                ON 
                    ur.user_id = ui.user_id
                JOIN
                    todoufuken AS td
                ON
                    ui.ken_code = td.ken_code
                
            WHERE
                ur.user_id = %s
            """
            cur.execute(sql, [user_id])
            user = cur.fetchone()

            sql = """
            SELECT
                sh.shikaku_name,
                us.user_id
            FROM
                shikaku AS sh
            JOIN
                user_shikaku AS us
            ON
                sh.shikaku_code = us.shikaku_code
            WHERE
                us.user_id = %s
            """
            cur.execute(sql, [user_id])
            shikaku_list = cur.fetchall()
            print("資格", shikaku_list)

# shikakulistをカンマ区切りで表示させたい。渡したい。
            user_shikaku = ""

            for shikaku in shikaku_list:
                user_shikaku += "," + shikaku['shikaku_name']
            
            user_shikaku = user_shikaku[1:]
            
            print("ユーザーの資格", user_shikaku)

            # new_user_list = []
            # user_id_list = []

            # for user in user_list:
            #     if new_user_list == []:
            #         new_user_list.append(user)
            #     else:
            #         new_user_list[0]['shikaku_name'] += f", {user['shikaku_name']}"
            # print(new_user_list)
            
            if user["gender"] == "1":
                user["gender"] = "男"

            else:
                user["gender"] = "女"
            # print(new_user_list[0])

    if 'mail' not in session:
        return redirect('/')

    return render_template(
        'user_detail.html', 
        user=user, 
        shikaku_list=shikaku_list, 
        user_shikaku=user_shikaku
    )

@app.get('/user_edit/<user_id>')
def user_edit(user_id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
            SELECT
                ur.user_id,
                ur.name,
                ui.name_kana,
                ui.gender,
                ur.password,
                ur.mail,
                ui.yubin,
                ui.ken_code,
                ui.jyusyo,
                td.ken_name
            FROM 
                users AS ur
                JOIN 
                    user_info AS ui
                ON 
                    ur.user_id = ui.user_id
                JOIN 
                    user_shikaku AS us
                ON 
                    ur.user_id = us.user_id
                JOIN
                    shikaku AS sh
                ON
                    us.shikaku_code = sh.shikaku_code
                JOIN
                    todoufuken AS td
                ON
                    ui.ken_code = td.ken_code
                
            WHERE
                ur.user_id = %s
            """

            cur.execute(sql, [user_id])
            user = cur.fetchone()
            
            sql = """
            SELECT
                us.shikaku_code,
                sh.shikaku_name
            FROM
                user_shikaku AS us
            JOIN
                shikaku AS sh
            ON
                us.shikaku_code = sh.shikaku_code
            WHERE
                us.user_id = %s
            """

            cur.execute(sql, [user_id])
            user_shikaku_list = cur.fetchall()

            sql = """
            SELECT
                ken_code
                , ken_name 
            FROM
                todoufuken
            """

            cur.execute(sql) 
            todoufuken_list = cur.fetchall()

            sql = """
            SELECT
                shikaku_code
                , shikaku_name 
            FROM
                shikaku
            """
            cur.execute(sql)
            shikaku_list = cur.fetchall()

            new_shikaku_list = []

            for shikaku in user_shikaku_list:
                new_shikaku_list.append(shikaku['shikaku_code'])

    if 'mail' not in session:
        return redirect('/')

    return render_template(
        'user_edit.html', 
        user=user, 
        todoufuken_list=todoufuken_list, 
        shikaku_list=shikaku_list, 
        new_shikaku_list=new_shikaku_list
    )

@app.get('/user_list')
def user_list():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
# 一般情報と資格情報を分けるために、sqlを分ける
            sql = """
            SELECT 
                ur.user_id, 
                ur.name
            FROM 
                users AS ur
            ORDER BY 
                ur.user_id DESC
            """
            cur.execute(sql)
            user_list = cur.fetchall()

            sql = """
            SELECT 
                us.user_id,
                us.shikaku_code,
                sh.shikaku_name
            FROM
                user_shikaku AS us
            JOIN 
                shikaku AS sh
            ON 
                us.shikaku_code = sh.shikaku_code
            """
            cur.execute(sql)
            user_shikaku_list = cur.fetchall()
            # print("資格", type(user_shikaku_list[0]["shikaku_name"]))


# idをkyeとして、shikakunameをvalueにいれる。
            shikaku_list = {}
            # shikaku_list["1"] = {}

            # for user in user_list:
            #     print(user)
            #     print(user["user_id"] + user["name"])
            #     shikaku_list[user[]]
            #     shikaku_list[user["user_id"]] = ""
            #     for shikaku in user_shikaku_list:
            #         if user["user_id"] == shikaku["user_id"]:
            #             shikaku_list[user["user_id"]] += shikaku["shikaku_name"]
            # print(shikaku_list)

# 一つ目のforでユーザーの情報（id,name）を回す。二つ目のforで資格情報を回し、idが一致した際にshikaku_nameを足していく（if文）。
            update_user = []
            for user in user_list:
                new_user = {}
                new_user["user_id"] = user["user_id"]
                new_user["name"] = user["name"]
                shikaku_list[user["user_id"]] = ""
                for shikaku in user_shikaku_list:
                    if user["user_id"] == shikaku["user_id"]:
                        shikaku_list[user["user_id"]] += "," + shikaku['shikaku_name']

                new_user["shikaku_name"] = shikaku_list[user["user_id"]][1:]
                update_user.append(new_user)
            # print("ユーザー", user)

# # チェックボックスの為の処理。二つの空リストに、
#             new_user_list = []
#             user_id_list = []

#             for user in user_list:
#                 if user['user_id'] not in user_id_list:
#                     new_user_list.append(user)
#                     user_id_list.append(user['user_id'])

#                 else:
#                     for new_user in new_user_list:
#                         if user['user_id'] == new_user['user_id']:
#                             new_user['shikaku_name'] += f", {user['shikaku_name']}"
    # print(user_list)

    if 'mail' not in session:
        return redirect('/')

    return render_template('user_list.html', user_list=update_user)

@app.post('/regist')
def regist():
    # 入力されたデータを渡す処理
    form = request.form
    # チェックボックスがある際に使う
    shikaku_list = request.form.getlist("shikaku_code")
    # print("性別", type(shikaku_list))
    # print("フォーム", form)
# バリデーションの処理
# 正規表現
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:

            is_error = False

            mail_pattern = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            password_pattern = "\A[a-z\d]{8,100}\Z(?i)"

            if form['name'] == "":
                is_error = True
                flash('※名前を入力してください', 'ng_name')
                
            if len(form['name']) >= 100:
                is_error = True
                flash('※名前が長すぎます（100文字以下）', 'ng_name')
                

            # 形式指定
            if form['mail'] == "":
                is_error = True
                flash('※メールアドレスを入力してください', 'ng_mail')
                
            if len(form['mail']) >= 100:
                is_error = True
                flash('※メールアドレスが長すぎます（100文字以下）', 'ng_mail')
                
            if not re.match(mail_pattern, form['mail']):
                is_error = True
                flash('※メールアドレスを正しく入力してください', 'ng_mail')
            
            sql = """
            SELECT 
                mail
            FROM 
                users
            WHERE
                mail = %s
            """
            cur.execute(sql, [form['mail']])
            user_mail = cur.fetchall()

            if len(user_mail) >= 1:
                is_error = True
                flash('※このメールアドレスは既に登録されています', 'ng_mail')

            # for mail_li in user_mail:
            #     if mail_li['mail'] == form['mail']:
            #         is_error = True
            #         flash('※このメールアドレスは既に登録されています', 'ng_mail')

                
            # 半角指定、数字指定
            if form['password'] == "":
                is_error = True
                flash('※パスワードを入力してください(半角英数字8文字以上100文字以下)', 'ng_pass')
                
            if len(form['password']) >= 100:
                is_error = True
                flash('※パスワードが長すぎます(半角英数字8文字以上100文字以下)', 'ng_pass')
                
            if not re.match(password_pattern, form['password']):
                is_error = True
                flash('※パスワードを正しく入力してください(半角英数字8文字以上100文字以下)', 'ng_pass')
                

        # 何かしら入力していなければならない場合は、not in 演算子を使う
            if 'gender' not in form:
                is_error = True
                flash('※性別を選択してください', 'ng_gender')
                

            if form['yubin'] == "":
                is_error = True
                flash('※郵便番号を入力してください', 'ng_yubin')
                
            if len(form['yubin']) >= 20:
                is_error = True
                flash('※郵便番号が長すぎます（20文字以下）', 'ng_yubin')
                

            if form['prefecture'] == "":
                is_error = True
                flash('※都道府県を選択してください', 'ng_pre')
                

            if form['adress'] == "":
                is_error = True
                flash('※住所を入力してください', 'ng_jyu')
                
            if len(form['adress']) >= 100:
                is_error = True
                flash('※住所が長すぎます（100文字以下）', 'ng_jyu')
                

            if is_error:
                return redirect('/create')


            sql = "select nextval('seq_user')"
            cur.execute(sql)
            user_id = cur.fetchone()[0]
            sql = """
            INSERT 
            INTO users(
                user_id, 
                name, 
                mail, 
                password, 
                status,
                lock_flag
            ) 
            VALUES (
                %s, 
                %s, 
                %s, 
                %s, 
                '0',
                '0'
            )
            """
            data = [
                user_id, 
                form['name'], 
                form['mail'], 
                generate_password_hash(form['password'])
            ]

            cur.execute(sql, data)
            sql = """
            INSERT 
            INTO user_shikaku(
                user_id, 
                shikaku_code
            ) 
            VALUES (
                %s, 
                %s
            )
            """

            for shikaku_code in shikaku_list:
                cur.execute(sql, [user_id, shikaku_code])

            sql = """
            INSERT 
            INTO user_info( 
                user_id
                , gender
                , yubin
                , ken_code
                , jyusyo
                , status
            ) 
            VALUES (  
                %s, 
                %s, 
                %s, 
                %s, 
                %s, 
                '0'
            )
            """
            cur.execute(sql, [
                user_id,     
                form['gender'], 
                form['yubin'], 
                form['prefecture'], 
                form['adress'], 
            ])
            conn.commit()

    print("debug")
    return redirect('/user_list')

# 更新はテーブル別にUPDATEの処理を行う
# ラストはcur.fetではなく、conn.commit()を使う（（INSERT, UPDATE, DELETE）

@app.post('/update/<user_id>')
def update(user_id):
    form = request.form 
    shikaku_list = request.form.getlist("shikaku_code")

    mail_pattern = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    password_pattern = "\A[a-z\d]{8,100}\Z(?i)"

    is_error = False

    if form['name'] == "":
        is_error = True
        flash('※名前を入力してください', 'ng_name')
    if len(form['name']) >= 100:
        is_error = True
        flash('※名前が長すぎます（100文字以下）', 'ng_name')
        

    if form['password'] == "":
        is_error = True
        flash('※パスワードを入力してください(半角英数字8文字以上100文字以下)', 'ng_pass')
    if len(form['password']) >= 100:
        is_error = True
        flash('※パスワードが長すぎます(半角英数字8文字以上100文字以下)', 'ng_pass')
    if not re.match(password_pattern, form['password']):
        is_error = True
        flash('※パスワードを正しく入力してください(半角英数字8文字以上100文字以下)', 'ng_pass')
        

    if form['mail'] == "":
        is_error = True
        flash('※メールアドレスを入力してください(半角英数字8文字以上100文字以下)', 'ng_mail')
    if len(form['mail']) >= 100:
        is_error = True
        flash('※メールアドレスが長すぎます（100文字以下）', 'ng_mail')
    if not re.match(mail_pattern, form['mail']):
        is_error = True
        flash('※メールアドレスを正しく入力してください', 'ng_mail')
        

    if 'num_of_inq' not in form:
        is_error = True
        flash('※性別を選択してください', 'ng_gender')
        

    if form['yubin'] == "":
        is_error = True
        flash('※郵便番号を入力してください', 'ng_yubin')
    if len(form['yubin']) >= 20:
        is_error = True
        flash('※郵便番号が長すぎます（20文字以下）', 'ng_yubin')
        
    if form['prefecture'] == "":
        is_error = True
        flash('※都道府県を選択してください', 'ng_pre')
        

    if form['adress'] == "":
        is_error = True
        flash('※住所を入力してください', 'ng_jyu')
    if len(form['adress']) >= 100:
        is_error = True
        flash('※住所が長すぎます（100文字以下）', 'ng_jyu')
        

    
    if is_error:
        return redirect(f'/user_edit/{user_id}')


    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            sql = """
            UPDATE
                users
            SET
                name = %s,
                password = %s,
                mail = %s
            WHERE
                user_id = %s
            """
            print(form)
            # %sの数だけcur.executeに渡すが、すべて書くとごちゃごちゃになる為、DATAとしてまとめてから渡している。中身はuser_editの名前をつかう。
            data = [
                form['name'], 
                form['password'],
                form['mail'],
                user_id
            ]

            cur.execute(sql, data)

            sql = """
            UPDATE
                user_info
            SET
                gender = %s,
                yubin = %s,
                ken_code = %s,
                jyusyo = %s
            WHERE
                user_id = %s
            """
            data = [
                form['num_of_inq'], 
                form['yubin'],
                form['prefecture'],
                form['adress'],
                user_id
            ]

            cur.execute(sql, data)

            # チェックボックスの値はUPDATEはめんどくさいから、DELETEで一度まっさらにしてからINSERTを使って入力していく。
            sql = """
            DELETE
            FROM
                user_shikaku
            WHERE
                user_id = %s
            """
            cur.execute(sql, [user_id])

            sql = """
            INSERT
            INTO user_shikaku(
                user_id,
                shikaku_code
            )
            VALUES(
                %s,
                %s
            )
            """

            # チェックボックスの値を受け取る.()の中にはキーを入れる。
            shikaku_list = request.form.getlist("skill")
            print(shikaku_list)

            for shikaku in shikaku_list:
                cur.execute(sql, [user_id, shikaku])


            # ラストのみ
            conn.commit()


    return redirect('/user_list')

@app.route('/logout') #ログアウト
def logout():
  session.pop('mail', None) #削除
  return redirect('/')


if __name__ == '__main__':
	app.run(debug=True)