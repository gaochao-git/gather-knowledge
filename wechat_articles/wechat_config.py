# 微信公众平台配置文件
# 请填入微信公众平台token和cookies

# 如何获取token和cookies:
# 1. 登录微信公众平台 https://mp.weixin.qq.com/
# 2. 打开浏览器开发者工具(F12)
# 3. 在Network标签中找到任意API请求
# 4. 复制请求头中的Cookie和URL中的token参数
# 5. 获取公众号的fakeid：在公众号管理页面的URL中可以找到

WECHAT_TOKEN = "286800424"
WECHAT_COOKIES = "appmsglist_action_3191976335=card; pac_uid=0_2byJ1eCnZDds7; suid=user_0_2byJ1eCnZDds7; _qimei_uuid42=19309111f061001c2791006eff9a7702b5bdd1b80c; _qimei_q36=; _qimei_h38=d9412cab2791006eff9a77020300000c119309; rewardsn=; wxtokenkey=777; ua_id=zphS6khOmp6OB1u6AAAAAPh6Q6fd2lOhqsSrkZjn4cU=; wxuin=52556465369698; mm_lang=zh_CN; sig=h017d960cf820c5feafc645d50b91305e12d2780c9613bcb5758c427913a3a7d902ae95a1de49cacbac; mmad_session=f7b77bd80c10661e7416817d2771b7696a2d48d708c4777a0621275f755a1fd14cb70f2b2899bdff92b8a8136f04bab8f1ef0a72e4b85275b0439c8a12a4f19024ae146da7aaaefa8302cbb3c921c26d5436613b99a177594527958fb0d692d411de1c56c245721266e7088080fefde3; pgv_info=ssid=s7852242340; pgv_pvid=4403369312; ts_uid=6603590528; cert=IOZzJudv4j8pLgIPw7OyLVlADjB3IiF5; _qimei_fingerprint=9d63cf19d8ffb8b88ef61aa237e8610e; poc_sid=HPyurmijYl3XgwBkoqBpPGXuKLVtYW-a9m-kqbgN; _clck=3191976335|1|fyu|0; uuid=5c4fa0ef809740029ccf2f6422c0d47c; rand_info=CAESIOJeJ/kod/Raib4Q+kd7XTZ5guhva5KDyxIxdxG3WWBo; slave_bizuin=3191976335; data_bizuin=3191976335; bizuin=3191976335; data_ticket=RKrxKkDEajDDhBVWYftomPO/p1lf6zKiZn+6UTjpnrijz2sCSZN43HSVA3ZGHa5k; slave_sid=OVV6QVlGU0tmUFNIdG41STJ4b05LbWt5cU5MU3BaaXVuQ2pCeDhPNWh3ZDJ6aUxJbkZIOUtWZVBEXzZLb0tadUdVTWVhNjFhVVljS3lBMm1seGJfcWxVQzJtNm0wRTRqc0FpUkxkekF4blFKSDN1VzUycU9zWUEyRVNlY3BBQWtxbFh5cXhhbW9SMTJtanFv; slave_user=gh_90e834f7a531; xid=b6f4a5c0a660d5343bf0a6adf9150ce1; _clsk=18ref43|1756419669846|4|1|mp.weixin.qq.com/weheat-agent/payload/record"
WECHAT_FAKEID = "MjM5NjAzNjM1Mg=="

# 注意：
# 1. token和cookies具有时效性，需要定期更新
# 2. 不要将包含真实token和cookies的配置文件上传到公共仓库
# 3. 可以通过环境变量的方式设置这些敏感信息
# 4. fakeid是可选的，如果不提供，系统会使用搜索方式作为备用