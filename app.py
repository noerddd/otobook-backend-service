import os
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from OpenAI import klasifikasiKeyword as keywords
from OpenAI import tajukSubjek as tajuk
from flask_jwt_extended import create_access_token, JWTManager, jwt_required, get_jwt_identity, create_refresh_token
import subprocess
from sqlalchemy import or_, func
import datetime
from sqlalchemy import Enum
import time

app = Flask(__name__)
CORS(app)
url = 'postgresql://postgres:postgres@localhost/Perpustakaan'


app.config['SQLALCHEMY_DATABASE_URI'] = url
db = SQLAlchemy(app)
migrate = Migrate(app, db)

UPLOAD_FOLDER = './uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_FOTOPROFILE = './fotoProfile/'
app.config['UPLOAD_FOTOPROFILE'] = UPLOAD_FOTOPROFILE
ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg', 'gif'}

app.config['JWT_SECRET_KEY'] = 'naplsdasdlkjasjfkmkj21kjklj4jkg12hgasf'
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=7)
jwt = JWTManager(app)

class MasterBuku(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, unique=True)
    judul = db.Column(db.String(250), nullable=False)
    pengarang = db.Column(db.String(250), nullable=False)
    penerbitan = db.Column(db.String(250), nullable=False)
    deskripsi = db.Column(db.String(250), nullable=False)
    isbn = db.Column(db.String(100), nullable=False, unique=True)
    userId = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    kota = db.Column(db.String(250), nullable=False)
    tahun_terbit = db.Column(db.String(250), nullable=False)
    editor = db.Column(db.String(250), nullable=False)
    ilustrator = db.Column(db.String(250), nullable=True)
    dateTime = db.Column(db.DateTime, nullable=True, default=db.func.now(), onupdate=db.func.now())
    kategori = db.Column(Enum('Diolah', 'Disumbangkan', name='kategori'), nullable=True, default='Diolah')

    # Menambahkan relasi dengan cascade delete dan nama backref yang unik
    cover_buku = db.relationship('CoverBuku', backref='master_buku_cover', cascade="all, delete-orphan", lazy=True)
    sinopsis_buku = db.relationship('SinopsisBuku', backref='master_buku_sinopsis', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f"<MasterBuku {self.id}>"

class CoverBuku(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    master_buku_id = db.Column(db.Integer, db.ForeignKey('master_buku.id'), nullable=False)
    cover = db.Column(db.String(250), nullable=False)
    path = db.Column(db.String(250), nullable=False)
    
    def __repr__(self):
        return f"<CoverBuku {self.id}>"

class SinopsisBuku(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sinopsis = db.Column(db.Text, nullable=False)
    keyword = db.Column(db.Text, nullable=False)
    no_class = db.Column(db.String(250), nullable=True)
    dateTime = db.Column(db.DateTime, nullable=True, default=db.func.now(), onupdate=db.func.now())
    master_buku_id = db.Column(db.Integer, db.ForeignKey('master_buku.id'), nullable=False, unique=True)
    
    def __repr__(self):
        return f"<SinopsisBuku {self.id}>"
    
class KlasifikasiBuku(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deweyNoClass = db.Column(db.String(250), nullable=False)    
    narasi_klasifikasi = db.Column(db.String(250), nullable=True)
    subject = db.Column(db.String(250), nullable=True)

    def __repr__(self):
        return f"<KlasifikasiBuku {self.id}>"

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(250), nullable=False) 
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    fotoprofile = db.Column(db.String(250), nullable=True)
    path = db.Column(db.String(250), nullable=True)
    dateTime = db.Column(db.DateTime, nullable=True, default=db.func.now(), onupdate=db.func.now())
    
    # menambahkan relasi dengan cascade delete dan nama backref yang unik
    master_buku = db.relationship('MasterBuku', backref='user', cascade="all, delete-orphan", lazy=True)
    
    def __init__(self, username, email, password) -> None:
        super().__init__()
        self.username = username
        self.email = email
        self.password = Bcrypt().generate_password_hash(password).decode('utf-8')
        
    def __repr__(self):
        return f"<User {self.id}>"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS


##### USER #####

# endpoint untuk menambahkan data user
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        user_email = User.query.filter_by(email=data['email']).first()
        if user_email:
            return jsonify({'message': 'Email sudah terdaftar'}), 400
        user = User(
            username=data['username'],
            email=data['email'],
            password=data['password']
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'message': 'User berhasil ditambahkan'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# endpoint untuk login
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data['email']).first()
        if user is None:
            return jsonify({'message': 'User tidak ditemukan'}), 404
        if Bcrypt().check_password_hash(user.password, data['password']):   
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            return jsonify({'access_token': access_token,'refresh_token':refresh_token ,'id' : user.id}), 200
        else:
            return jsonify({'message': 'Password salah'}), 400
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)  # Hanya menerima refresh token
def refresh():
    current_user = get_jwt_identity()  # Dapatkan user dari refresh token
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200

# get user
@app.route('/api/getUser', methods=['GET'])
def getUser():
    try:
        user = User.query.all()
        userList = []
        for u in user:
            userList.append({
                'id': u.id,
                'username': u.username,
                'email': u.email,
            })
        return jsonify({"data":userList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# get  user 
@app.route('/api/getUser/<id>', methods=['GET'])
def getUserLogin(id):
    try:
        user = User.query.filter_by(id=id).first()
        if user is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'fotoprofile' : user.fotoprofile,
            'path' : user.path
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# edit user by id
@app.route('/api/editUser/<id>', methods=['PUT'])
def editUser(id):
    try:
        user = User.query.filter_by(id=id).first()
        if user is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404

        # Jika ada file dalam permintaan, tangani sebagai form-data
        if 'file' in request.files:
            file = request.files['file']
            print(f"file diterima: {file}")
            if file.filename == '':
                return jsonify({'message': 'No selected file'}), 400
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOTOPROFILE'], filename))
                master = {
                    'username': request.form.get('username', user.username),
                    'email': request.form.get('email', user.email),
                    'fotoprofile': filename,
                    'path': f'/fotoProfile/{filename}'
                }
                for key, value in master.items():
                    setattr(user, key, value)
                db.session.commit()
                return jsonify({'message': 'Data berhasil diubah'}), 200
            else:
                return jsonify({'message': 'File tidak valid'}), 400
        # Jika tidak ada file, harapkan data dalam bentuk JSON
        elif request.content_type == 'application/json':
            data = request.get_json()
            master = {
                'username': data.get('username', user.username),
                'email': data.get('email', user.email)
            }
            for key, value in master.items():
                setattr(user, key, value)
            db.session.commit()
            return jsonify({'message': 'Data berhasil diubah'}), 200
        else:
            return jsonify({'message': 'Unsupported Media Type'}), 415

    except Exception as e:
        return jsonify({'message': str(e)}), 400


@app.route('/fotoProfile/<filename>', methods=['GET'])
def get_profile(filename):
    return send_from_directory(app.config['UPLOAD_FOTOPROFILE'], filename)

# logout
@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        # Hanya kembalikan pesan sukses
        return jsonify({'message': 'Logout berhasil'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

##### BUKU #####

# endpoint untuk menambahkan data buku
@app.route('/api/addBuku/<id>', methods=['POST'])
def addBuku(id):
    try:
        data = request.get_json()
        # user_id = User.query.filter_by(id=id).first()
        ilustrator = data.get('ilustrator', None)
        kategori = data.get('kategori', None)
        buku = MasterBuku(
            judul = data['judul'],
            isbn = data['isbn'],
            pengarang = data['pengarang'],
            penerbitan = data['penerbitan'],
            deskripsi = data['deskripsi'],
            kota = data['kota'],
            tahun_terbit = data['tahun'],
            editor = data['editor'],
            kategori = kategori,
            ilustrator = ilustrator,
            userId = id
        )
        isbn = MasterBuku.query.filter_by(isbn=data['isbn']).first()
        if isbn:
            return jsonify({'message': 'ISBN sudah terdaftar'}), 400
        db.session.add(buku)
        db.session.commit()
        return jsonify({'message': 'Data berhasil ditambahkan'}),201
    except Exception as e:
        return jsonify({'message': e}), 400
    
# get buku sesuai dengan user yang membuat
@app.route('/api/getBuku', methods=['GET'])
# @jwt_required()
def getBuku():
    try:
        # Ambil userId dari query parameters
        user_id = request.args.get('userId')

        # Cek apakah userId diberikan
        if not user_id:
            return jsonify({'message': 'userId is required'}), 400

        # Cari buku sesuai dengan userId
        buku = MasterBuku.query.filter_by(userId=user_id).all()

        # Jika tidak ada buku ditemukan untuk user tersebut
        if not buku:
            return jsonify({'message': 'Tidak ada buku '}), 200

        # Buat daftar buku untuk dikembalikan
        bukuList = []
        for b in buku:
            bukuList.append({
                'id': b.id,
                'judul': b.judul,
                'pengarang': b.pengarang,
                'penerbitan': b.penerbitan,
                'deskripsi': b.deskripsi,
                'isbn': b.isbn,
                'kota' : b.kota,
                'tahun_terbit' : b.tahun_terbit,
                'editor' : b.editor,
                'ilustrator' : b.ilustrator,
                'kategori' : b.kategori,
            })
        # Kembalikan daftar buku dalam format JSON
        return jsonify({"data": bukuList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400


@app.route('/api/getBook', methods=['GET'])
# @jwt_required()
def getBook():
    try:
        # Ambil userId dari query parameters
        user_id = request.args.get('userId')

        # Cek apakah userId diberikan
        if not user_id:
            return jsonify({'message': 'userId is required'}), 400

        # Cari buku sesuai dengan userId
        buku = MasterBuku.query.filter_by(userId=user_id).all()

        # Jika tidak ada buku ditemukan untuk user tersebut
        if not buku:
            return jsonify({'message': 'Tidak ada buku '}), 200

        # Buat daftar buku untuk dikembalikan
        bukuList = []
        for b in buku:
            bukuList.append({
                'id': b.id,
                'judul': b.judul,
                'pengarang': b.pengarang,
                'penerbitan': b.penerbitan,
                'deskripsi': b.deskripsi,
                'isbn': b.isbn,
                'kota' : b.kota,
                'tahun_terbit' : b.tahun_terbit,
                'editor' : b.editor,
                'ilustrator' : b.ilustrator,
                'kategori' : b.kategori,
            })
        # Kembalikan daftar buku dalam format JSON
        return jsonify({"data": bukuList}), 200

    except Exception as e:
        return jsonify({'message': str(e)}), 400

# get buku and sinopsis
@app.route('/api/getBukuSinopsis', methods=['GET'])
def getBukuSinopsis():
    try:
        buku = MasterBuku.query.all()
        sinopsis = SinopsisBuku.query.all()
        bukuList = []
        for b in buku:
            for s in sinopsis:
                if b.id == s.master_buku_id:
                    bukuList.append({
                        'id': b.id,
                        'judul': b.judul,
                        'pengarang': b.pengarang,
                        'penerbitan': b.penerbitan,
                        'deskripsi': b.deskripsi,
                        'isbn': b.isbn,
                        'kota' : b.kota,
                        'tahun_terbit' : b.tahun_terbit,
                        'editor' : b.editor,
                        'ilustrator' : b.ilustrator,
                        'kategori' : b.kategori,
                        'sinopsis': s.sinopsis,
                        'keyword': s.keyword
                    })
        return jsonify({"data":bukuList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
# get buku by id 
@app.route("/api/getBuku/<id>", methods=['GET'])
# @jwt_required()
def getBukuById(id):
    buku = MasterBuku.query.filter_by(id=id).first()
    if buku is None:
        return jsonify({'message': 'Data tidak ditemukan'}), 404
    return jsonify({
        'id': buku.id,
        'judul': buku.judul,
        'pengarang': buku.pengarang,
        'penerbitan': buku.penerbitan,
        'deskripsi': buku.deskripsi,
        'isbn': buku.isbn,
        'kota' : buku.kota,
        'tahun' : buku.tahun_terbit,
        'editor' : buku.editor,
        'ilustrator' : buku.ilustrator,
        'kategori' : buku.kategori
    }), 200

# edit buku by id
@app.route('/api/editBuku/<id>', methods=['PUT'])
def editBuku(id):
    try:
        buku = MasterBuku.query.filter_by(id=id).first()
        if buku is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        data = request.get_json()
        master = {
            'judul': data['judul'],
            'pengarang': data['pengarang'],
            'penerbitan': data['penerbitan'],
            'deskripsi': data['deskripsi'],
            'isbn': data['isbn'],
            'kota' : data['kota'],
            'tahun_terbit' : data['tahun_terbit'],
            'editor' : data['editor'],
            'ilustrator' : data['ilustrator'],
            'kategori' : data['kategori']
        }
        for key, value in master.items():
            setattr(buku, key, value)
        db.session.commit()
        return jsonify({'message': 'Data berhasil diubah'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400



# delete buku by id
@app.route('/api/deleteBuku/<id>', methods=['DELETE'])
def deleteBuku(id):
    try:
        buku = MasterBuku.query.filter_by(id=id).first()
        if buku is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        db.session.delete(buku)
        db.session.commit()
        return jsonify({'message': 'Data berhasil dihapus'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400


# add cover
@app.route('/api/uploadCover/<master_buku_id>', methods=['POST'])
def uploadCover(master_buku_id):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cover = CoverBuku(
            master_buku_id = master_buku_id,
            cover = filename,
            path=f'uploads/{filename}'
        )
        db.session.add(cover)
        db.session.commit()
        return jsonify({'message': 'Cover berhasil diupload'}), 201
    else:
        return jsonify({'message': 'File tidak valid'}), 400

# get cover by id
@app.route('/api/getCover/<master_buku_id>', methods=['GET'])
def getCover(master_buku_id):
    cover = CoverBuku.query.filter_by(master_buku_id=master_buku_id).first()
    if cover is None:
        return jsonify({'message': 'Data tidak ditemukan'}), 404
    return jsonify({
        'id': cover.id,
        'master_buku_id': cover.master_buku_id,
        'cover': cover.cover,
        'path': f'/uploads/{cover.cover}'
    }), 200
    

@app.route('/uploads/<filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    

# edit cover by id
@app.route('/api/editCover/<id>', methods=['PUT'])
def editCover(id):
    try:
        cover = CoverBuku.query.filter_by(id=id).first()
        if cover is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        data = request.get_json()
        master = {
            'master_buku_id': data['master_buku_id'],
            'cover': data['cover'],
            'path': data['path']
        }
        for key, value in master.items():
            setattr(cover, key, value)
        db.session.commit()
        return jsonify({'message': 'Data berhasil diubah'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
# delete cover by id
@app.route('/api/deleteCover/<id>', methods=['DELETE'])
def deleteCover(id):
    try:
        cover = CoverBuku.query.filter_by(id=id).first()
        if cover is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        db.session.delete(cover)
        db.session.commit()
        return jsonify({'message': 'Data berhasil dihapus'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
# add sinopsis
@app.route('/api/addSinopsis/<master_buku_id>', methods=['POST'])
def addSinopsis(master_buku_id):
    try:
        data = request.get_json()
        sinopsis = SinopsisBuku(
            sinopsis = data['sinopsis'],
            keyword = data['keyword'],
            no_class = data['no_class'],
            master_buku_id = master_buku_id
        )
        db.session.add(sinopsis)
        db.session.commit()
        return jsonify({'message': 'Data berhasil ditambahkan'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# get sinopsis by master_buku_id
@app.route('/api/getSinopsis/<master_buku_id>', methods=['GET'])
# @jwt_required()
def getSinopsis(master_buku_id):
    try:
        sinopsis = SinopsisBuku.query.filter_by(master_buku_id=master_buku_id).first()
        if sinopsis is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        return jsonify({
            'id': sinopsis.id,
            'sinopsis': sinopsis.sinopsis,
            'keyword': sinopsis.keyword,
            'no_class': sinopsis.no_class,
            'master_buku_id': sinopsis.master_buku_id
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
@app.route('/api/getklasifikasi', methods=['POST'])
def klasifikasi():
    try:
        start_time = time.time()
        data = request.get_json()

        result = keywords.generate_keywords_watsonx(data['sinopsis'])

        duration = time.time() - start_time
        result["duration"] = f"{duration:.2f} seconds"

        return jsonify(result), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400



# get book and sinopsis by id
@app.route('/api/getBookSinopsis/<id>', methods=['GET'])
def getBookSinopsis(id):
    try:
        buku = MasterBuku.query.filter_by(id=id).first()
        if buku is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        sinopsis = SinopsisBuku.query.filter_by(master_buku_id=id).first()
        # if sinopsis is None:
        #     return jsonify({'message': 'Data tidak ditemukan'}), 404
        return jsonify({
            'id' : buku.id,
            'judul': buku.judul,
            'pengarang': buku.pengarang,
            'penerbitan': buku.penerbitan,
            'deskripsi': buku.deskripsi,
            'isbn': buku.isbn,
            'kota': buku.kota,
            'tahun': buku.tahun_terbit,
            'editor': buku.editor,
            'ilustrator': buku.ilustrator,
            'kategori': buku.kategori,
            'sinopsis': sinopsis.sinopsis if sinopsis and sinopsis.sinopsis else None,
            'keyword': sinopsis.keyword if sinopsis and sinopsis.keyword else None,
            'no_class': sinopsis.no_class if sinopsis and sinopsis.no_class else None
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
# edit sinopsis and buku by id
@app.route('/api/editBookSinopsis/<id>', methods=['PUT'])
def editBookSinopsis(id):
    try:
        buku = MasterBuku.query.filter_by(id=id).first()
        if not buku:
            return jsonify({'message' : 'Buku tidak di temukan'})
        data = request.get_json()
        
         # Cek apakah ISBN yang baru sudah ada di database (kecuali untuk buku yang sedang di-update)
        isbn_exists = MasterBuku.query.filter(MasterBuku.isbn == data['isbn'], MasterBuku.id != id).first()
        if isbn_exists:
            return jsonify({'message': 'ISBN sudah terdaftar'}), 400
        
        books = {
            'judul': data.get('judul'),
            'pengarang': data.get('pengarang'),
            'penerbitan': data.get('penerbitan'),
            'deskripsi': data.get('deskripsi'),
            'isbn': data.get('isbn'),
            'kota' : data.get('kota'),
            'tahun_terbit' : data.get('tahun_terbit'),
            'editor' : data.get('editor'),
            'ilustrator' : data.get('ilustrator'),
            'kategori' : data.get('kategori')
        }
        for key, value in books.items():
            setattr(buku, key , value)
        sinopsis = SinopsisBuku.query.filter_by(master_buku_id=id).first()
        if not sinopsis:
            return jsonify({'message' : 'sinopsis tidak di temukan'})
        sinops = {
            'sinopsis': data.get('sinopsis'),
            'keyword': data.get('keyword'),
            'no_class' : data.get('no_class')
        }
        for key, value in sinops.items():
            setattr(sinopsis, key, value)
        db.session.commit()
        return jsonify({'message': 'Data berhasil diubah'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
@app.route('/api/run-automation/<id>', methods=['POST'])
def run_automation(id):
    try:
        data = request.get_json()
        buku = MasterBuku.query.filter_by(id=id).first()
        book_id = buku.id
        kode_wilayah = data.get('kodeWilayah')
        ip_address = data.get('ipAddress')
        username = data.get('username')
        password = data.get('password')
        
        absolute_robot_path= '/home/otobook/RPA-uiInlis/tasks.robot'
        
        # Path ke file Robot Framework
        result = subprocess.run(
            [
                '/home/otobook/.local/bin/robot', 
                '--variable', f'BOOK_ID:{book_id}',
                '--variable', f'KODE_WILAYAH:{kode_wilayah}',
                '--variable', f'IP_ADDRESS:{ip_address}',
                '--variable', f'USERNAME_USER:{username}',
                '--variable', f'PASSWORD_USER:{password}',
                absolute_robot_path
            ], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Log output hasil subprocess
        stdout_log = result.stdout
        stderr_log = result.stderr

        return jsonify({"message": "Data berhasil dimasukkan!", "stdout": stdout_log, "stderr": stderr_log}), 200

    except subprocess.CalledProcessError as e:
        # Tampilkan pesan error dari subprocess
        return jsonify({"error": f"Subprocess error: {str(e)}", "stderr": e.stderr}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# search buku by keyword
@app.route('/api/searchBuku', methods=['POST'])
def searchBuku():
    try:
        data = request.get_json()
        # sinopsis = SinopsisBuku.query.filter(SinopsisBuku.keyword.like(f"%{keyword['keyword']}%")).all()
        bukuList = []
        sinopsis = SinopsisBuku.query.filter(or_(SinopsisBuku.keyword.ilike(f"%{data['keyword']}%"), MasterBuku.judul.ilike(f"%{data['keyword']}%"))).join(MasterBuku, SinopsisBuku.master_buku_id == MasterBuku.id).all()
        for s in sinopsis:
           bukuList.append({
                'id': s.master_buku_id,
                'judul': s.master_buku_sinopsis.judul,  # Akses melalui backref
                'pengarang': s.master_buku_sinopsis.pengarang,
                'penerbitan': s.master_buku_sinopsis.penerbitan,
                'deskripsi': s.master_buku_sinopsis.deskripsi,
                'isbn': s.master_buku_sinopsis.isbn,
                'kota' : s.master_buku_sinopsis.kota,
                'tahun_terbit' : s.master_buku_sinopsis.tahun_terbit,
                'editor' : s.master_buku_sinopsis.editor,
                'ilustrator' : s.master_buku_sinopsis.ilustrator,
                'sinopsis': s.sinopsis,
                'keyword': s.keyword,
                'no_class' : s.no_class,
                'kategori' : s.master_buku_sinopsis.kategori
            })
        # buku tanpa sinopsis dan keyword
        buku_query = MasterBuku.query.filter(MasterBuku.judul.ilike(f"%{data['keyword']}%")).outerjoin(SinopsisBuku, MasterBuku.id == SinopsisBuku.master_buku_id).filter(SinopsisBuku.id.is_(None)).all()
        for b in buku_query:
            bukuList.append({
                'id': b.id,
                'judul': b.judul,
                'pengarang': b.pengarang,
                'penerbitan': b.penerbitan,
                'deskripsi': b.deskripsi,
                'isbn': b.isbn,
                'kota' : b.kota,
                'tahun_terbit' : b.tahun_terbit,
                'editor' : b.editor,
                'ilustrator' : b.ilustrator,
                'kategori' : b.kategori,
                'sinopsis': None,
                'keyword': None,
                'no_class': None
            })
        # search buku mengunakan sinopsis 
        scanIsbn = data['keyword'].replace("-","")
        isbn = MasterBuku.query.filter(func.replace(MasterBuku.isbn, "-", "").ilike(f"%{scanIsbn}%")).outerjoin(SinopsisBuku, MasterBuku.id == SinopsisBuku.master_buku_id).filter(SinopsisBuku.id.is_(None)).all()
        for i in isbn:
            bukuList.append({
                'id': i.id,
                'judul': i.judul,
                'pengarang': i.pengarang,
                'penerbitan': i.penerbitan,
                'deskripsi': i.deskripsi,
                'isbn': i.isbn,
                'kota' : i.kota,
                'tahun_terbit' : i.tahun_terbit,
                'editor' : i.editor,
                'ilustrator' : i.ilustrator,
                'kategori' : i.kategori,
                'sinopsis': None,
                'keyword': None,
                'no_class' : None
            })
        isbnAll = SinopsisBuku.query.filter(or_(SinopsisBuku.keyword.ilike(f"%{data['keyword']}%"), func.replace(MasterBuku.isbn, "-", "").ilike(f"%{scanIsbn}%"))).join(MasterBuku, SinopsisBuku.master_buku_id == MasterBuku.id).all()    
        for c in isbnAll:
            bukuList.append({
                'id': c.master_buku_id,
                'judul': c.master_buku_sinopsis.judul,  # Akses melalui backref
                'pengarang': c.master_buku_sinopsis.pengarang,
                'penerbitan': c.master_buku_sinopsis.penerbitan,
                'deskripsi': c.master_buku_sinopsis.deskripsi,
                'isbn': c.master_buku_sinopsis.isbn,
                'kota' : c.master_buku_sinopsis.kota,
                'tahun_terbit' : c.master_buku_sinopsis.tahun_terbit,
                'kategori' : c.master_buku_sinopsis.kategori,
                'editor' : c.master_buku_sinopsis.editor,
                'ilustrator' : c.master_buku_sinopsis.ilustrator,
                'sinopsis': c.sinopsis,
                'keyword': c.keyword,
                'no_class' : c.no_class
            })
        return jsonify({"data":bukuList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

##### klasifikasi buku #####

# get klasifikasi buku
@app.route('/api/getKlasifikasiBuku', methods=['GET'])
def getklasifikasi():
    try:
        klasifikasi = KlasifikasiBuku.query.all()
        if not klasifikasi:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        klasifikasilist = []
        for k in klasifikasi:
            klasifikasilist.append({
                'id': k.id,
                'deweyNoClass': k.deweyNoClass,
                'narasi_klasifikasi': k.narasi_klasifikasi,
                'subject': k.subject
            }), 
        return jsonify({"data" : klasifikasilist}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# add klasifikasi buku
@app.route('/api/addKlasfikasi', methods=['POST'])
def addKlasfikasi():
    try:
        data = request.get_json()
        klasifikasi = KlasifikasiBuku(
            deweyNoClass = data['deweyNoClass'],
            narasi_klasifikasi = data['narasi_klasifikasi'],
            subject = data['subject']
        )
        if KlasifikasiBuku.query.filter_by(deweyNoClass=data['deweyNoClass']).first():
            return jsonify({'message': 'Klasifikasi sudah terdaftar'}), 400
        db.session.add(klasifikasi)
        db.session.commit()
        return jsonify({'message': 'Data berhasil ditambahkan'}), 201
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# get by id klasifikasi buku
@app.route('/api/getKlasifikasiBuku/<id>', methods=['GET'])
def getKlasifikasiById(id):
    try:
        klasifikasi = KlasifikasiBuku.query.filter_by(id=id).first()
        return jsonify({
            'id': klasifikasi.id,
            'deweyNoClass': klasifikasi.deweyNoClass,
            'narasi_klasifikasi': klasifikasi.narasi_klasifikasi,
            'subject': klasifikasi.subject
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# edit klasifikasi buku by id
@app.route('/api/editKlasifikasi/<id>', methods=['PUT'])
def editKlasifikasi(id):
    try:
        klasifikasi = KlasifikasiBuku.query.filter_by(id=id).first()
        if not klasifikasi:
            return jsonify({'message' : 'Klasifikasi tidak di temukan'})
        data = request.get_json()
        klas = {
            'deweyNoClass': data.get('deweyNoClass'),
            'narasi_klasifikasi': data.get('narasi_klasifikasi'),
            'subject': data.get('subject')
        }
        # cek apakah deweyNoClass yang baru sudah ada di database (kecuali untuk klasifikasi yang sedang di-update)
        deweyNoClass_exists = KlasifikasiBuku.query.filter(KlasifikasiBuku.deweyNoClass == data['deweyNoClass'], KlasifikasiBuku.id != id).first()
        if deweyNoClass_exists:
            return jsonify({'message': 'deweyNoClass sudah terdaftar'}), 400
        for key, value in klas.items():
            setattr(klasifikasi, key , value)
        db.session.commit()
        return jsonify({'message': 'Data berhasil diubah'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
# delete klasifikasi buku by id
@app.route('/api/deleteKlasifikasi/<id>', methods=['DELETE'])
def deleteKlasifikasi(id):
    try:
        klasifikasi = KlasifikasiBuku.query.filter_by(id=id).first()
        if klasifikasi is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        db.session.delete(klasifikasi)
        db.session.commit()
        return jsonify({'message': 'Data berhasil dihapus'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# search klasifikasi by all 
@app.route('/api/searchKlasifikasi', methods=['POST'])
def searchKlasifikasi():
    try:
        data = request.get_json()
        keyword = data.get('keyword', '')
        if not keyword:
            return jsonify({'message': 'Keyword is required'}), 400
        search = [
            KlasifikasiBuku.deweyNoClass.ilike(f"%{keyword}%"),
            KlasifikasiBuku.narasi_klasifikasi.ilike(f"%{keyword}%"),
            KlasifikasiBuku.subject.ilike(f"%{keyword}%")
        ]
        klasifikasi = KlasifikasiBuku.query.filter(or_(*search)).all()
        klasifikasiList = []
        for k in klasifikasi:
            klasifikasiList.append({
                'id': k.id,
                'deweyNoClass': k.deweyNoClass,
                'narasi_klasifikasi': k.narasi_klasifikasi,
                'subject': k.subject
            })
        return jsonify({"data":klasifikasiList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400

# mengirim foto cover buku
@app.route('/api/sendCover/<id>', methods=['GET'])
def getCoverBuku(id):
    try:
        cover = CoverBuku.query.filter_by(master_buku_id=id).first()
        if cover is None:
            return jsonify({'message': 'Data tidak ditemukan'}), 404
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], cover.cover)
        if os.path.exists(full_path):
            return send_file(full_path, mimetype='png/jpg/jpeg' ,as_attachment=True)
        else:
            return jsonify({'message': 'File tidak ditemukan'}), 404
    except Exception as e:
        return jsonify({'message': str(e)}), 400

def ocr_processing(image_bytes):
    # Load image for OCR
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert to RGB (if needed)
    image = image.convert('RGB')
    
    # Convert to numpy array
    image_np = np.array(image)
    
    # OCR processing
    results = ocr.ocr(image_np, cls=True)  # Menggunakan PaddleOCR untuk OCR
    
    formatted_results = []
    for result in results:
        for line in result:
            box = line[0]  # Bounding box coordinates
            text = line[1][0]  # Extracted text
            formatted_results.append([box, [text]])
    
    return formatted_results

# Rute POST untuk memproses gambar
@app.route('/process_image', methods=['POST'])
def process_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        image_bytes = file.read()
        ocr_result = ocr_processing(image_bytes)
        return jsonify({
            'image': base64.b64encode(image_bytes).decode('utf-8'),
            'ocr_result': ocr_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/BukuDiolah', methods= ['GET'])
def getBukuDiolah():
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'message': 'userId is required'}), 400

        buku = MasterBuku.query.filter_by(userId=user_id).filter(MasterBuku.kategori == 'Diolah').all()

        if not buku:
            return jsonify({'message': 'Tidak ada buku '}), 200

        bukuList = []
        for b in buku:
            bukuList.append({
                'id': b.id,
                'judul': b.judul,
                'pengarang': b.pengarang,
                'penerbitan': b.penerbitan,
                'deskripsi': b.deskripsi,
                'isbn': b.isbn,
                'kota' : b.kota,
                'tahun_terbit' : b.tahun_terbit,
                'editor' : b.editor,
                'ilustrator' : b.ilustrator,
                'kategori' : b.kategori,
            })
        return jsonify({"data": bukuList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
# kategori disumbangkan
@app.route('/api/BukuDisumbangkan', methods= ['GET'])
def getBukuDisumbangkan():
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'message': 'userId is required'}), 400

        buku = MasterBuku.query.filter_by(userId=user_id).filter(MasterBuku.kategori == 'Disumbangkan').all()

        if not buku:
            return jsonify({'message': 'Tidak ada buku '}), 200

        bukuList = []
        for b in buku:
            bukuList.append({
                'id': b.id,
                'judul': b.judul,
                'pengarang': b.pengarang,
                'penerbitan': b.penerbitan,
                'deskripsi': b.deskripsi,
                'isbn': b.isbn,
                'kota' : b.kota,
                'tahun_terbit' : b.tahun_terbit,
                'editor' : b.editor,
                'ilustrator' : b.ilustrator,
                'kategori' : b.kategori,
            })
        # Kembalikan daftar buku dalam format JSON
        return jsonify({"data": bukuList}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 400


@app.route('/api/download', methods=['GET'])
def download():
    try:
        user_id = request.args.get('userId')
        if not user_id:
            return jsonify({'message': 'userId is required'}), 400
        buku = MasterBuku.query.filter_by(userId=user_id).filter(MasterBuku.kategori == 'Disumbangkan').all()
        if not buku:
            return jsonify({'message': 'Tidak ada buku '}), 200
        marks_data = pd.DataFrame({
            'id': [b.id for b in buku],
            'judul': [b.judul for b in buku],
            'pengarang': [b.pengarang for b in buku],
            'penerbitan': [b.penerbitan for b in buku],
            'deskripsi': [b.deskripsi for b in buku],
            'isbn': [b.isbn for b in buku],
            'kota' : [b.kota for b in buku],
            'tahun_terbit' : [b.tahun_terbit for b in buku],
            'editor' : [b.editor for b in buku],
            'ilustrator' : [b.ilustrator for b in buku],
            'kategori' : [b.kategori for b in buku]
        })
        file_name = 'buku_disumbangkan.xlsx'
        marks_data.to_excel(file_name, index=False)
        return send_file(file_name, as_attachment=True)
    except Exception as e:
        return jsonify({'message': str(e)}), 400
    
if __name__ == '__main__':
    app.run(debug=False)
