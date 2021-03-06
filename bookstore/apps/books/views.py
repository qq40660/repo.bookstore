#coding=utf-8
#
# Copyright (C) 2013  Kliyes.com  All rights reserved.
#
# author: JingYang.
#
# This file is part of BookStore.

import json

from django.shortcuts import render_to_response
from django.template.context import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required
from django.template.loader import get_template
from django.core.urlresolvers import reverse

from common import pages
from books.models import Book, Cart, Order, BookComment, Category
import datetime
from django.db.models.query_utils import Q
from django.core import serializers

BOOK_DATA_KEY = "bookPaging"
BOOK_PAGE_SIZE = 10
CMT_DATA_KEY = "cmtPaging"
CMT_PAGE_SIZE = 5

def _getDataKey(type):
    ''''''
    if type == 'cate':
        return 'cateBookData'
    elif type == 'name': 
        return 'nameBookData'
    elif type == 'all':
        return 'allBookData'
        

def goHome(request):
    '''首页, index.html'''
    ids= []
    allCates = Category.objects.getAllCates()
    bestsellers = Book.objects.getBestsellers()
    hotTwo = Book.objects.getBestsellers(2)
    for ht in hotTwo:
        ids.append(ht.id)
        
    books = _sortBooks(Book.objects.getAll().exclude(id__in=ids))
    
    ctx = {'allCates': allCates, 'bestsellers': bestsellers, 'hotTwo': hotTwo, 
           'cateName': 'all'}
    bookPaging = initSessionBooklistPaging(request, _getDataKey('cate'), books, BOOK_PAGE_SIZE)
    if bookPaging:
        ctx.update(bookPaging.result(1))
    
    return render_to_response('index.html', RequestContext(request, ctx))

def initSessionBooklistPaging(request, dataKey, booklist, pageSize):
    ''''''
    return pages.setSessionPaging(request, dataKey, booklist, pageSize)

def initSessionCmtlistPaging(request, dataKey, cmtlist, pageSize):
    ''''''
    return pages.setSessionPaging(request, dataKey, cmtlist, pageSize)

def _sortBooks(books, key='soldCount'):
    '''按关键字key对books进行排序'''
    if key == 'soldCount':
        return books.order_by('-bought_count')
    elif key == 'price':
        return books.order_by('-price')
    elif key == 'cmtsCount':
        return books.order_by('-comment_count')
    elif key == 'regDate':
        return books.order_by('-reg_date')
    elif key == 'pubDate':
        return books.order_by('-publish_date')
    else:
        return None

def getBooksByCate(request, cateName):
    '''按书籍分类显示书籍, ajax request only'''
    key = request.REQUEST.get('key', 'soldCount')
    if not cateName:
        return
    
    ids = []
    if cateName == 'all':
        hotTwo = Book.objects.getBestsellers(2)
        for ht in hotTwo:
            ids.append(ht.id)
        books = Book.objects.getAll().exclude(id__in=ids)
    else:
        category = Category.objects.get(name=cateName)
        hotTwo = Book.objects.getHotTwoByCate(category)
        for ht in hotTwo:
            ids.append(ht.id)
        books = Book.objects.filter(category=category).exclude(id__in=ids)
    
    books = _sortBooks(books, key)
        
    ctx = {'type': 'cate', 'cateName': cateName}
    
    bookPaging = initSessionBooklistPaging(request, _getDataKey('cate'), books, BOOK_PAGE_SIZE)
    if bookPaging:
        ctx.update(bookPaging.result(1))
    
    t = get_template('base/books_list.html')
    html = t.render(RequestContext(request, ctx))
    
    t2 = get_template('base/hot_two_books.html')
    html2 = t2.render(RequestContext(request, {'hotTwo': hotTwo}))
    
    return HttpResponse(json.dumps({'html': html, 'html2': html2, 'status': 'success'}))

def getBooksByName(request):
    '''按书名模糊查询书籍'''
    name = request.REQUEST.get('name', '')
    books = Book.objects.filter(Q(name__icontains=name) | Q(desc__icontains=name))
    ctx = {'type': 'name'}
    
    bookPaging = initSessionBooklistPaging(request, _getDataKey('name'), books, BOOK_PAGE_SIZE)
    if bookPaging:
        ctx.update(bookPaging.result(1))
    
    return render_to_response('books/bookset.html', RequestContext(request, ctx))

def pagingBooks(request, type):
    '''处理书籍查询结果分页, ajax request only'''
    if not request.is_ajax():
        raise Http404
    
    pageNo = pages.getRequestPageNo(request)
    request.session['currentPageNo'] = pageNo
    paging = pages.getSessionPaging(request, _getDataKey(type))
    if not paging:
        booklist = Book.objects.all()
        paging = initSessionBooklistPaging(request, _getDataKey(type), booklist, BOOK_PAGE_SIZE)
    
    t = get_template('books/includes/resultlist.html')
    html = t.render(RequestContext(request, paging.result(pageNo)))
    
    return HttpResponse(json.dumps({'status': 'success', 'html': html}))

def pagingAll(request):
    '''处理首页所有书籍分页, ajax request only'''
    if not request.is_ajax():
        raise Http404
    
    cateName = request.REQUEST.get('cateName', 'all')
    ctx = {'cateName': cateName}
    
    pageNo = pages.getRequestPageNo(request)
    request.session['currentPageNo'] = pageNo
    paging = pages.getSessionPaging(request, _getDataKey('cate'))
    if not paging:
        if cateName == 'all':
            books = Book.objects.getAll()
        else:
            category = Category.objects.get(name=cateName)
            books = Book.objects.filter(category=category)
            
        paging = initSessionBooklistPaging(request, _getDataKey('cate'), books, BOOK_PAGE_SIZE)
    
    ctx.update(paging.result(pageNo))
    t = get_template('base/books_list.html')
    html = t.render(RequestContext(request, ctx))
    
    return HttpResponse(json.dumps({'status': 'success', 'html': html}))

def _getBookById(bookId):
    '''按书籍的id号查找书籍'''
    try:
        book = Book.objects.get(id=bookId)
    except Book.DoesNotExist:
        return False
    
    return book

def _getCmtsPercent(cmtsCount, allCmtsCount):
    '''计算cmtsCount在allCmtsCount中的比例'''
    if allCmtsCount == 0:
        return 0
    
    return (cmtsCount / float(allCmtsCount)) * 100

def bookDetail(request, bookId):
    book = _getBookById(bookId)
    if not book:
        return HttpResponse(u'查无此书')
    
    recommend = book.category.getRecommendExceptBook(book)
    newer = book.category.getNewerExceptBook(book)
    
    allCommentsCount = book.countAllComments()
    
    ctx = {'book': book, 'otherBooks': book.author.getOtherBooks(book),
           'recommend': recommend, 'newer': newer, 'allCmtsCount': allCommentsCount, 
           'positiveCmtsPercent': _getCmtsPercent(book.countPositiveComments(), allCommentsCount), 
           'normalCmtsPercent': _getCmtsPercent(book.countNormalComments(), allCommentsCount), 
           'negativeCmtsPercent': _getCmtsPercent(book.countNegativeComments(), allCommentsCount)}
    
    ctx.update(_initCmtsData(request, book.getAllComments(), "all"))
    ctx.update(_initCmtsData(request, book.getPositiveComments(), "positive"))
    ctx.update(_initCmtsData(request, book.getNormalComments(), "normal"))
    ctx.update(_initCmtsData(request, book.getNegativeComments(), "negative"))
    
    return render_to_response('books/bookdetail.html', RequestContext(request, ctx))

def _initCmtsData(request, cmts, keyPrefix):
    ctx = {}
    if cmts:
        cmtPaging = initSessionCmtlistPaging(request, _getCmtsDataKey(keyPrefix), cmts, 5)
        if cmtPaging:
            ctx.update(cmtPaging.result(1, pageItemsKey=keyPrefix+'PageItems', 
                                        pageRangeKey=keyPrefix+'PageRange'))
        
    return ctx
    
@login_required
def addToCart(request, bookId):
    '''加入购物车, ajax request only'''
    if not request.is_ajax:
        raise Http404
    
    book = _getBookById(bookId)
    if not book:
        return HttpResponse(u'查无此书')
    
    profile = request.user.get_profile()
    cart = Cart.objects.get(owner=profile)
    if cart.getItemByBook(book):
        return HttpResponse(json.dumps({'status': 'failed'}))
    
    if not cart.addBookItem(book):
        return HttpResponse(json.dumps({'status': 'failed'}))
    
    return HttpResponse(json.dumps({'status': 'success'}))

@login_required
def delFromCart(request, bookId):
    '''从购物车中移除书籍, ajax request only'''
    if not request.is_ajax:
        raise Http404
    
    book = _getBookById(bookId)
    if not book:
        return HttpResponse(u'查无此书')
    
    profile = request.user.get_profile()
    cart = Cart.objects.get(owner=profile)
    if not cart.removeBookItem(book):
        return HttpResponse(json.dumps({'status': 'failed'}))
    
    return HttpResponse(json.dumps({'status': 'success'}))

@login_required
def checkCart(request):
    '''查看购物车'''
    profile = request.user.get_profile()
    cart = Cart.objects.get(owner=profile)
    
    return render_to_response('books/bookcart.html', RequestContext(request, 
        {'cart': cart, 'itemCount': len(cart.getItems())}))

@login_required
def makeOrder(request):
    '''填写订单'''
    profile = request.user.get_profile()
    cart = Cart.objects.get(owner=profile)
    
    if not request.is_ajax() or not cart.getBooks():
        return render_to_response('books/bookorder.html', RequestContext(request, 
            {'cart': cart}))
    
    for book in cart.getBooks():
        try:
            amount = request.REQUEST.get('amount_'+str(book.id), '1')
            if int(amount) < 1:
                raise Exception
            bookItem = cart.getItemByBook(book)
            bookItem.amount = int(amount)
            bookItem.save()
            bookItem.fee = bookItem.setFee()
        except Exception:
            return HttpResponse(json.dumps({'status': 'failed'}))
        
    return HttpResponse(json.dumps({'status': 'success'}))

@login_required
def submitOrder(request):
    '''提交订单, post request only'''
    if request.method != "POST":
        raise Http404
    
    profile = request.user.get_profile()
    cart = Cart.objects.get(owner=profile)
    
    addr = request.REQUEST.get('addr', '')
    contact = request.REQUEST.get('contact', '')
    receiver = request.REQUEST.get('receiver', '')
    makeDefault = request.REQUEST.get('default', '')
    
    if makeDefault == 'on':
        profile.receiver = receiver
        profile.addr = addr
        profile.contact = contact
        profile.save()
        
    now = datetime.datetime.now()
    
    order = Order()
    order.owner = profile
    order.total_fee = cart.getTotalFee()
    order.receiver = receiver
    order.addr = addr
    order.contact = contact
    order.save()
    # 订单编号由日期加订单ID号组成, 如201305180000018, 表示2013年5月18号产生的订单ID为18的订单
    order.code = str(now.year) + ('%02i' % now.month) + ('%02i' % now.day) + ('%07i' % order.id) 
    order.save()
    # 提交订单后清空购物车中书籍
    profile.buyBooks(cart.getBooks())
    if cart.moveToOrder(order):
        cart.clearCart()
    
    return HttpResponseRedirect(reverse("thanks"))

@login_required
def goComment(request, bookId):
    '''跳转至评论页面'''
    book = _getBookById(bookId)
    if not book:
        raise Http404
    
    return render_to_response('books/comment.html', 
        RequestContext(request, {'book': book}))


@login_required    
def addComment(request, bookId):
    '''添加书籍评论'''
    if request.method != "POST":
        raise Http404
    
    content = request.REQUEST.get('content', '')
    grade = request.REQUEST.get('grade', 4)
    
    profile = request.user.get_profile()
    book = _getBookById(bookId)
    book.addComment(profile, content, grade)
    
    return HttpResponseRedirect('/books/comment_done/?bookId=%s' % book.id)

def commentDone(request):
    '''完成评论'''
    bookId = request.REQUEST.get('bookId', None)
    return render_to_response('books/comment_done.html', RequestContext(request, 
        {'bookId': bookId}))

def pagingCmts(request, bookId):
    '''处理书籍评论分页, ajax request only'''
    if not request.is_ajax():
        raise Http404
    
    book = _getBookById(bookId)
    pageNo = pages.getRequestPageNo(request)
    
    request.session['currentPageNo'] = pageNo
    paging = pages.getSessionPaging(request, CMT_DATA_KEY)
    if not paging:
        cmts = book.getComments()
        paging = initSessionCmtlistPaging(request, CMT_DATA_KEY, cmts, CMT_PAGE_SIZE)
    
    t = get_template('books/includes/comments.html')
    ctx = paging.result(pageNo)
    html = t.render(RequestContext(request,ctx))
    
    return HttpResponse(json.dumps({'status': 'success', 'html': html}))


def _getCmtsDataKey(keyPrefix):
    return "%s%s" % (keyPrefix, 'cmtsPaging')

def pagingBookCmts(request, bookId):
    ''''''
    if not request.is_ajax():
        raise Http404
    
    book = _getBookById(bookId)
    pageNo = pages.getRequestPageNo(request)
    column = request.REQUEST.get("column", '')
    
    request.session['currentPageNo'] = pageNo
    paging = pages.getSessionPaging(request, _getCmtsDataKey(column))
    if not paging:
        cmtList = book.getComments()
        paging = initSessionCmtlistPaging(request, _getCmtsDataKey(column), cmtList, 5)
    
    t = get_template('books/includes/cmtlist_%s.html' % column)
    return HttpResponse(json.dumps({'status': "success", 
        'html': t.render(RequestContext(
         request, paging.result(pageNo, 
               pageItemsKey=column+"PageItems",
               pageRangeKey=column+"PageRange",
    )))}))


def test_serializer(request):
    data = serializers.serialize("json", Book.objects.all(), 
        use_natural_keys=True)
    print 'type:', type(data)
    return HttpResponse(data)
