# -*- coding: UTF-8 -*-
# nohup python3 HTTP_SERVER.py >> ../HTTP_SERVER.log 2>&1 &
__version__ = "0.6.0"
__all__ = ["MyHTTPRequestHandler"]

import os
import time
import sys
import socket
import posixpath
import platform
try:
    from html import escape
except ImportError:
    from cgi import escape
import shutil
import mimetypes
import re
import signal
from io import BytesIO
import codecs
import base64  # 添加base64模块用于处理认证
if sys.version_info.major == 3:
    # Python3
    from urllib.parse import quote  
    from urllib.parse import unquote
    from http.server import HTTPServer
    from http.server import BaseHTTPRequestHandler
else:
    # Python2
    from urllib import quote
    from urllib import unquote
    from BaseHTTPServer import HTTPServer
    from BaseHTTPServer import BaseHTTPRequestHandler

"""
带有GET/HEAD/POST命令的简单HTTP请求处理程序。
提供来自当前目录及其任何子目录的文件,可以接收客户端上传的文件和文件夹。
GET/HEAD/POST请求完全相同，只是HEAD请求忽略了文件的实际内容。
"""


class MyHTTPRequestHandler(BaseHTTPRequestHandler):

    server_version = "simple_http_server/" + __version__

    mylist = []
    myspace = ""
    treefile = "dirtree.txt"
    IPAddress = socket.gethostbyname(socket.gethostname())

    # 添加用户名和密码
    USERNAME = 'admin'
    PASSWORD = 'password'

    def check_auth(self):
        '''检查基本认证'''
        auth_header = self.headers.get('Authorization')
        if auth_header is None:
            self.send_auth_headers()
            return False
        else:
            auth_type, encoded_credentials = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                self.send_auth_headers()
                return False
            decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded_credentials.split(':', 1)
            if self.validate_credentials(username, password):
                return True
            else:
                self.send_auth_headers()
                return False

    def send_auth_headers(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Login Required"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Authentication required.')

    def validate_credentials(self, username, password):
        return username == self.USERNAME and password == self.PASSWORD

    def buildTree(self, url):
        print("directories url:", url)
        files = os.listdir(r''+url)
        # not show parent directory
        # self.mylist = []buildTree(
        for file in files:
            if not file.startswith('.'):
                myfile = url + "/"+file
                size_str = bytes_conversion(myfile)
                if os.path.isfile(myfile):
                    self.mylist.append(
                        str(self.myspace)+"|____"+file + " " + size_str+"\n")
                elif os.path.isdir(myfile):
                    self.mylist.append(
                        str(self.myspace)+"|____"+file + "\n")
                    # get into the sub-directory, add "|    "
                    self.myspace = self.myspace+"|    "
                    self.buildTree(myfile)
                    # when sub-directory of iteration is finished, reduce "|    "
                    self.myspace = self.myspace[:-5]


    def getAllFilesList(self):
        listofme = []
        for root, dirs, files in os.walk(translate_path(self.path)):
            files.sort()
            for fi in files:
                display_name = os.path.join(root, fi)
                # 删除前面的n个字符，取出相对当前目录的路径
                relative_path = display_name[len(
                    os.getcwd()):].replace('\\', '/')[1:]
                if not relative_path.startswith('.'):
                    # print("display", display_name)
                    st = os.stat(display_name)
                    # fsize = st.st_size
                    fsize = bytes_conversion(display_name)
                    print("Size", str(os.path.getsize(display_name)))
                    fmtime = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
                    listofme.append(relative_path+"\t")
                    listofme.append(fsize+"\t")
                    listofme.append(str(fmtime)+"\t\n")
        return listofme

    def calculate_dir_size(self, pathvar):
        '''
        calculate dir size(bytes)
        '''
        size = 0
        lst = os.listdir(pathvar)
        for i in lst:
            pathnew = os.path.join(pathvar, i)
            if os.path.isfile(pathnew):
                size += os.path.getsize(pathnew)
            elif os.path.isdir(pathnew):
                size += self.calculate_dir_size(pathnew)
        return size

    def writeList(self, url):
        tree_ = self.getAllFilesList()
        f = open(url, 'w', encoding="utf-8")
        f.write("http://"+str(self.IPAddress) +
                ":8000/ \ndirectory tree\n")
        # self.mylist.sort()
        f.writelines(self.mylist)
        f.write("\nFile Path\tFile Size\tFile Modify Time\n")
        f.writelines(tree_)
        self.mylist = []
        self.myspace = ""
        print("writing completed.")
        f.close()

    def do_GET(self):
        """Serve a GET request."""
        if not self.check_auth():
            return
        paths = unquote(self.path)
        path = str(paths)
        # print("url path ===", path)
        plist = path.split("/", 2)
        # print("plist", plist)
        if len(plist) > 2 and plist[1] == "delete":
            result = plist[2]
            print("ready delete file/dir===>", result)
            if isWondows() and result.startswith("/"):
                result = result[1:]
            if os.path.exists(result):
                print("deleting file/dir===>", result)
                if os.path.isdir(result):
                    shutil.rmtree(result)
                else:
                    os.remove(result)
                time.sleep(0.5)
                # 0.5s后重定向
                self.send_response(302)
                self.send_header('Location', "/")
                self.end_headers()
                return
        fd = self.send_head()
        if fd:
            shutil.copyfileobj(fd, self.wfile)
            # 只有回到根目录下才更新写入目录文件，保持最新
            if path == "/":
                self.mylist = []
                self.buildTree(translate_path(self.path))
                self.writeList(self.treefile)
            fd.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        if not self.check_auth():
            return
        fd = self.send_head()
        if fd:
            fd.close()

    def do_POST(self):
        """Serve a POST request."""
        if not self.check_auth():
            return
        r, info = self.deal_post_data()

        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong><br>")
        else:
            f.write(b"<strong>Failed:</strong><br>")

        for i in info:
            print(r, i, "by: ", self.client_address)
            f.write(i.encode('utf-8')+b"<br>")
        f.write(b"<br><a href=\"%s\">back</a>" %
                self.headers['referer'].encode('ascii'))
        f.write(b"</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()
        self.mylist = []
        # 每次提交post请求之后更新目录树文件
        self.buildTree(translate_path(self.path))
        self.writeList(MyHTTPRequestHandler.treefile)

    def str_to_chinese(self, var):
        not_end = True
        while not_end:
            start1 = var.find("\\x")
            if start1 > -1:
                str1 = var[start1 + 2:start1 + 4]
                start2 = var[start1 + 4:].find("\\x") + start1 + 4
                if start2 > -1:
                    str2 = var[start2 + 2:start2 + 4]

                    start3 = var[start2 + 4:].find("\\x") + start2 + 4
                    if start3 > -1:
                        str3 = var[start3 + 2:start3 + 4]
            else:
                not_end = False
            if start1 > -1 and start2 > -1 and start3 > -1:
                str_all = str1 + str2 + str3
                str_all = codecs.decode(str_all, "hex").decode('utf-8')

                str_re = var[start1:start3 + 4]
                var = var.replace(str_re, str_all)
        return var

    def deal_post_data(self):
        boundary = self.headers["Content-Type"].split("=")[1].encode('ascii')
        print("boundary===", boundary)
        remain_bytes = int(self.headers['content-length'])
        print("remain_bytes===", remain_bytes)

        res = []
        line = self.rfile.readline()
        while boundary in line and str(line, encoding="utf-8")[-4:] != "--\r\n":

            remain_bytes -= len(line)
            if boundary not in line:
                return False, "Content NOT begin with boundary"
            line = self.rfile.readline()
            remain_bytes -= len(line)
            print("line!!!", line)
            fn = re.findall(
                r'Content-Disposition.*name="file"; filename="(.*)"', str(line))
            if not fn:
                return False, "Can't find out file name..."
            path = translate_path(self.path)

            fname = fn[0]
            fname = self.str_to_chinese(fname)
            print("------", fname)

            fn = os.path.join(path, fname)
            while os.path.exists(fn):
                fn += "_"
            print("!!!!", fn)
            dirname = os.path.dirname(fn)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            line = self.rfile.readline()
            remain_bytes -= len(line)
            line = self.rfile.readline()
            # b'\r\n'
            remain_bytes -= len(line)
            try:
                out = open(fn, 'wb')
            except IOError:
                return False, "Can't create file to write, do you have permission to write?"

            pre_line = self.rfile.readline()
            print("pre_line", pre_line)
            remain_bytes -= len(pre_line)
            print("remain_bytes", remain_bytes)
            Flag = True
            while remain_bytes > 0:
                line = self.rfile.readline()
                print("while line", line)

                if boundary in line:
                    remain_bytes -= len(line)
                    pre_line = pre_line[0:-1]
                    if pre_line.endswith(b'\r'):
                        pre_line = pre_line[0:-1]
                    out.write(pre_line)
                    out.close()
                    res.append("File '%s' upload success!" % fn)
                    Flag = False
                    break
                else:
                    out.write(pre_line)
                    pre_line = line
            if pre_line is not None and Flag == True:
                out.write(pre_line)
                out.close()
                res.append("File '%s' upload success!" % fn)
        return True, res

    def send_head(self):
        """Common code for GET and HEAD commands."""
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode.
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        # Fix Messy Display
        self.send_header("Content-type", content_type+";charset=utf-8")
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing."""
        try:
            list_dir = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list_dir.sort(key=lambda a: a.lower())
        f = BytesIO()
        display_path = escape(unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<head>\n<title> \xe6\x96\x87\xe4\xbb\xb6\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x9c\x8d\xe5\x8a\xa1\xe5\x99\xa8 %s</title>\n" %
                display_path.encode('utf-8'))
        # 添加CSS样式
        f.write(b'''<style>
body { font-family: Arial, sans-serif; }
h2 { color: #2E8B57; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
th { background-color: #f2f2f2; }
a { text-decoration: none; color: #1E90FF; }
a:hover { text-decoration: underline; }
</style>
''')
        f.write(b"</head>\n")
        f.write(b"<body>\n<h2>Root Directory %s</h2>\n" %
                display_path.encode('utf-8'))
        f.write(b"<hr>\n")
        # 上传目录
        f.write(b"<h3>Folder Upload</h3>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(
            b"<input ref=\"input\" webkitdirectory multiple name=\"file\" type=\"file\"/>")
        f.write(b"<input type=\"submit\" value=\"Upload Folder\"/></form>\n")
        f.write(b"<hr>\n")
        # 上传文件
        f.write(b"<h3>File Upload</h3>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input ref=\"input\" multiple name=\"file\" type=\"file\"/>")
        f.write(b"<input type=\"submit\" value=\"Upload File\"/></form>\n")

        f.write(b"<hr>\n")
        # 表格
        f.write(b"<table>")
        f.write(b"<tr><th>Path</th>")
        f.write(b"<th>Type</th>")
        f.write(b"<th>Size</th>")
        f.write(b"<th>Modify Time</th>")
        f.write(b"<th>Operation</th>")
        f.write(b"</tr>")

        # 根目录下所有的内容
        for name in list_dir:
            fullname = os.path.join(path, name)
            display_name = linkname = name
            if not display_name.startswith('.'):
                if display_name == "HTTP_SERVER.py" or display_name == "_config.yml":
                    continue

                st = os.stat(fullname)
                if os.path.isdir(fullname):
                    fsize = bytes_conversion(
                        "", self.calculate_dir_size(fullname))
                else:
                    fsize = bytes_conversion(fullname)
                fmtime = time.strftime(
                    '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
                relative_path = fullname[len(
                    os.getcwd()):].replace('\\', '/')
                f.write(b"<tr>")
                f.write(b'<td><a href="%s">%s</a></td>' % (
                    quote(relative_path).encode('utf-8'), escape("/"+display_name).encode('utf-8')))
                ftype = "file"
                if os.path.isdir(fullname):
                    ftype = "dir"
                elif os.path.isfile(fullname):
                    ftype = "file"
                f.write(b"<td>%s</td>" %
                        escape(ftype).encode('utf-8'))
                f.write(b"<td>%s</td>" %
                        escape(fsize).encode('utf-8'))
                f.write(b"<td>%s</td>" %
                        escape(fmtime).encode('ascii'))
                f.write(b"<td><a style='border: solid 1px red; text-decoration: none; background: red; color: white;' href=\"/delete/%s\">delete</a>" %
                        escape(fullname).encode('utf-8'))
                f.write(b"</tr>")

        f.write(b"</table>")
        f.write(b"\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def guess_type(self, path):
        """Guess the type of a file."""
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        '.txt': 'text/plain',
    })


def isWondows():
    '''
    判断当前运行平台
    :return:
    '''
    sysstr = platform.system()
    if (sysstr == "Windows"):
        return True
    elif (sysstr == "Linux"):
        return False
    else:
        print("Other System ")
    return False


def translate_path(path):
    """Translate a /-separated PATH to the local filename syntax."""
    # abandon query parameters
    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]
    path = posixpath.normpath(unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = os.getcwd()
    for word in words:
        drive, word = os.path.splitdrive(word)
        head, word = os.path.split(word)
        if word in (os.curdir, os.pardir):
            continue
        path = os.path.join(path, word)
    return path


def bytes_conversion(file_path, total_size=-1):
    """
    calculate file size and dynamically convert it to K, M, GB, etc.
    :param file_path:
    :param total_size: the size of a dir
    :return: file size with format
    """
    number = 0
    if total_size == -1:
        number = os.path.getsize(file_path)
    else:
        number = total_size
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = dict()
    for a, s in enumerate(symbols):
        prefix[s] = 1 << (a + 1) * 10
    for s in reversed(symbols):
        if int(number) >= prefix[s]:
            value = float(number) / prefix[s]
            return '%.2f%s' % (value, s)
    return "%sB" % number


def signal_handler(signal, frame):
    print("You choose to stop me.")
    exit()


def main():
    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = 1234
    server_address = ('', port)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    server = httpd.socket.getsockname()
    print("server_version: " + MyHTTPRequestHandler.server_version +
          ", python_version: " + MyHTTPRequestHandler.sys_version)
    print("Serving HTTP on: " +
          str(server[0]) + ", port: " + str(server[1]) + " ...")
    httpd.serve_forever()


if __name__ == '__main__':
    main()
