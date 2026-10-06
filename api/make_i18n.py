"""بيولّد js/i18n.js من القاموس اللي تحت.

ليه سكريبت بدل ما نكتب الـ JS بإيدنا؟ عشان القاموس ٦ لغات × ١١٠ مفاتيح.
مكتوب كده، كل مفتاح سطر واحد وترجماته جنبه — سهل تشوف الناقص.
"""
import json, pathlib

# key: [en, ar, tr, sw, zh, ru]
D = {
    # ----------------------------------------------------------------- nav --
    "nav.dashboard": ["Dashboard", "الرئيسية", "Panel", "Dashibodi", "主页", "Главная"],
    "nav.meals":     ["Meals", "الوجبات", "Yemekler", "Milo", "餐食", "Блюда"],
    "nav.compare":   ["Compare", "المقارنة", "Karşılaştır", "Linganisha", "比较", "Сравнить"],
    "nav.game":      ["Game", "اللعبة", "Oyun", "Mchezo", "游戏", "Игра"],
    "nav.settings":  ["Settings", "الإعدادات", "Ayarlar", "Mipangilio", "设置", "Настройки"],

    # -------------------------------------------------------------- chrome --
    "chrome.signIn":    ["Sign in", "تسجيل الدخول", "Giriş yap", "Ingia", "登录", "Войти"],
    "chrome.synced":    ["Synced", "متزامن", "Eşitlendi", "Imesawazishwa", "已同步", "Синхронизировано"],
    "chrome.syncing":   ["Syncing…", "جاري المزامنة…", "Eşitleniyor…", "Inasawazisha…", "同步中…", "Синхронизация…"],
    "chrome.offline":   ["Offline", "غير متصل", "Çevrimdışı", "Nje ya mtandao", "离线", "Не в сети"],
    "chrome.setArea":   ["Set your area", "حدّد منطقتك", "Bölgeni seç", "Weka eneo lako", "设置您的地区", "Укажите район"],
    "chrome.signedInAs": ["Signed in as", "مسجّل الدخول كـ", "Giriş yapan", "Umeingia kama", "登录为", "Вы вошли как"],
    "chrome.expired":   ["Your sign-in has expired", "انتهت جلستك", "Oturumun sona erdi", "Kipindi chako kimeisha", "登录已过期", "Сессия истекла"],
    "chrome.language":  ["Language", "اللغة", "Dil", "Lugha", "语言", "Язык"],
    "chrome.backToApp": ["Back to the app", "رجوع للتطبيق", "Uygulamaya dön", "Rudi kwenye programu", "返回应用", "Вернуться в приложение"],

    # ----------------------------------------------------------- dashboard --
    "dash.loading":     ["Loading…", "جاري التحميل…", "Yükleniyor…", "Inapakia…", "加载中…", "Загрузка…"],
    "dash.meal":        ["meal", "وجبة", "yemek", "mlo", "餐", "блюдо"],
    "dash.meals":       ["meals", "وجبات", "yemek", "milo", "餐", "блюд"],
    "dash.market":      ["market", "محل", "market", "duka", "商店", "магазин"],
    "dash.markets":     ["markets", "محلات", "market", "maduka", "商店", "магазинов"],
    "dash.fullyPriced": ["fully priced", "مسعّرة بالكامل", "tam fiyatlı", "zenye bei kamili", "已完整定价", "с полными ценами"],
    "dash.start":       ["Start by adding a meal.", "ابدأ بإضافة وجبة.", "Bir yemek ekleyerek başla.", "Anza kwa kuongeza mlo.", "先添加一份餐食。", "Начните с добавления блюда."],
    "dash.goToMeals":   ["Go to Meals", "اذهب للوجبات", "Yemeklere git", "Nenda kwa Milo", "前往餐食", "К блюдам"],
    "dash.addPrices":   ["Add prices for one meal at every market and the comparison appears here.",
                         "ضيف أسعار وجبة واحدة في كل المحلات وهتلاقي المقارنة هنا.",
                         "Bir yemeğin fiyatlarını her markette gir, karşılaştırma burada görünsün.",
                         "Weka bei za mlo mmoja katika kila duka, ulinganisho utaonekana hapa.",
                         "为一份餐食在每个商店添加价格，比较结果将显示在这里。",
                         "Добавьте цены одного блюда во всех магазинах — сравнение появится здесь."],
    "dash.goToCompare": ["Go to Compare", "اذهب للمقارنة", "Karşılaştırmaya git", "Nenda kwa Linganisha", "前往比较", "К сравнению"],
    "dash.yourMeals":   ["Your meals", "وجباتك", "Yemeklerin", "Milo yako", "您的餐食", "Ваши блюда"],
    "dash.editMeals":   ["Edit meals", "تعديل الوجبات", "Yemekleri düzenle", "Hariri milo", "编辑餐食", "Изменить блюда"],
    "dash.noIngredients": ["No ingredients yet", "مفيش مكوّنات لسه", "Henüz malzeme yok", "Bado hakuna viungo", "尚无食材", "Пока нет ингредиентов"],
    "dash.noPrices":    ["no prices yet", "مفيش أسعار لسه", "henüz fiyat yok", "bado hakuna bei", "尚无价格", "цен пока нет"],
    "dash.ingredient":  ["ingredient", "مكوّن", "malzeme", "kiungo", "食材", "ингредиент"],
    "dash.ingredients": ["ingredients", "مكوّنات", "malzeme", "viungo", "食材", "ингредиентов"],
    "dash.of":          ["of", "من", "/", "kati ya", "/", "из"],
    "dash.priced":      ["priced", "مسعّر", "fiyatlı", "zenye bei", "已定价", "с ценой"],
    "dash.at":          ["at", "في", "—", "katika", "于", "в"],
    "dash.cheapestPlace": ["Cheapest place to buy everything", "أرخص محل تشتري منه كل حاجة", "Her şeyi almak için en ucuz yer", "Mahali rahisi zaidi kununua kila kitu", "购买所有商品最便宜的地方", "Где всё дешевле всего"],

    # --------------------------------------------------------------- meals --
    "meals.title":      ["Your meals", "وجباتك", "Yemeklerin", "Milo yako", "您的餐食", "Ваши блюда"],
    "meals.new":        ["+ New meal", "+ وجبة جديدة", "+ Yeni yemek", "+ Mlo mpya", "+ 新餐食", "+ Новое блюдо"],
    "meals.add":        ["Add", "إضافة", "Ekle", "Ongeza", "添加", "Добавить"],
    "meals.cancel":     ["Cancel", "إلغاء", "İptal", "Ghairi", "取消", "Отмена"],
    "meals.namePh":     ["Meal name, e.g. Butter chicken", "اسم الوجبة، مثلاً كبسة", "Yemek adı, örn. Tavuk pilav", "Jina la mlo, mf. Pilau", "餐食名称，例如 黄油鸡", "Название блюда, напр. Плов"],
    "meals.mealName":   ["Meal name", "اسم الوجبة", "Yemek adı", "Jina la mlo", "餐食名称", "Название блюда"],
    "meals.ingredients": ["Ingredients", "المكوّنات", "Malzemeler", "Viungo", "食材", "Ингредиенты"],
    "meals.empty":      ["Nothing in this meal yet.", "الوجبة دي فاضية لسه.", "Bu yemekte henüz bir şey yok.", "Hakuna kitu kwenye mlo huu bado.", "这份餐食还是空的。", "В этом блюде пока ничего нет."],
    "meals.noMeals":    ["No meals yet. Add one above, then list what goes into it.",
                         "مفيش وجبات لسه. ضيف واحدة فوق، وبعدين اكتب مكوّناتها.",
                         "Henüz yemek yok. Yukarıdan bir tane ekle, sonra içindekileri yaz.",
                         "Bado hakuna milo. Ongeza mmoja juu, kisha orodhesha viungo vyake.",
                         "尚无餐食。先在上方添加一份，再列出食材。",
                         "Блюд пока нет. Добавьте одно выше, затем перечислите состав."],
    "meals.addIngPh":   ["Add an ingredient…", "ضيف مكوّن…", "Malzeme ekle…", "Ongeza kiungo…", "添加食材…", "Добавить ингредиент…"],
    "meals.qty":        ["Qty", "الكمية", "Miktar", "Kiasi", "数量", "Кол-во"],
    "meals.unit":       ["unit", "وحدة", "birim", "kipimo", "单位", "ед."],
    "meals.priceItUp":  ["Price it up →", "سعّرها →", "Fiyatla →", "Weka bei →", "定价 →", "Оценить →"],
    "meals.remove":     ["Remove", "حذف", "Kaldır", "Ondoa", "移除", "Удалить"],
    "meals.added":      ["Added", "اتضافت", "Eklendi", "Imeongezwa", "已添加", "Добавлено"],
    "meals.deleted":    ["Deleted", "اتمسحت", "Silindi", "Imefutwa", "已删除", "Удалено"],
    "meals.deleteAsk":  ["Delete", "امسح", "Sil", "Futa", "删除", "Удалить"],
    "meals.andPrices":  ["and every price in it?", "وكل الأسعار اللي فيها؟", "ve içindeki tüm fiyatlar silinsin mi?", "na bei zote ndani yake?", "及其中所有价格？", "и все цены в нём?"],

    # ------------------------------------------------------------- compare --
    "cmp.title":        ["Compare prices", "قارن الأسعار", "Fiyatları karşılaştır", "Linganisha bei", "比较价格", "Сравнить цены"],
    "cmp.meal":         ["Meal", "الوجبة", "Yemek", "Mlo", "餐食", "Блюдо"],
    "cmp.perItem":      ["Cheapest per item", "الأرخص لكل صنف", "Ürün başına en ucuz", "Rahisi zaidi kwa kila kitu", "单品最便宜", "Дешевле по позиции"],
    "cmp.everyMarket":  ["Every market", "كل المحلات", "Tüm marketler", "Kila duka", "所有商店", "Все магазины"],
    "cmp.bestMarket":   ["Cheapest market", "أرخص محل", "En ucuz market", "Duka rahisi zaidi", "最便宜的商店", "Самый дешёвый магазин"],
    "cmp.getPrices":    ["Get prices from", "هات الأسعار من", "Fiyatları şuradan al", "Pata bei kutoka", "从以下来源获取价格", "Получить цены из"],
    "cmp.addPrice":     ["add price", "ضيف سعر", "fiyat ekle", "weka bei", "添加价格", "добавить цену"],
    "cmp.ingredient":   ["Ingredient", "المكوّن", "Malzeme", "Kiungo", "食材", "Ингредиент"],
    "cmp.total":        ["Total", "الإجمالي", "Toplam", "Jumla", "合计", "Итого"],
    "cmp.totalEach":    ["Total, buying each item wherever it’s cheapest",
                         "الإجمالي، لو اشتريت كل صنف من أرخص مكان",
                         "Her ürünü en ucuz yerden alırsan toplam",
                         "Jumla, ukinunua kila kitu mahali rahisi zaidi",
                         "合计：每样都在最便宜处购买",
                         "Итого, если покупать каждое там, где дешевле"],
    "cmp.stillUnpriced": ["still unpriced.", "لسه من غير سعر.", "hâlâ fiyatsız.", "bado hazina bei.", "仍未定价。", "ещё без цены."],
    "cmp.missing":      ["missing", "ناقص", "eksik", "hakuna", "缺失", "не хватает"],
    "cmp.noMeals":      ["No meals yet.", "مفيش وجبات لسه.", "Henüz yemek yok.", "Bado hakuna milo.", "尚无餐食。", "Блюд пока нет."],
    "cmp.addOne":       ["Add one first.", "ضيف واحدة الأول.", "Önce bir tane ekle.", "Ongeza mmoja kwanza.", "请先添加一份。", "Сначала добавьте одно."],
    "cmp.noMarkets":    ["No markets yet.", "مفيش محلات لسه.", "Henüz market yok.", "Bado hakuna maduka.", "尚无商店。", "Магазинов пока нет."],
    "cmp.addMarket":    ["Add a market", "ضيف محل", "Bir market ekle", "Ongeza duka", "添加商店", "Добавить магазин"],
    "cmp.toCompare":    ["to compare against.", "عشان تقارن بيه.", "karşılaştırmak için.", "ili kulinganisha.", "以便进行比较。", "чтобы было с чем сравнивать."],
    "cmp.noWinner":     ["No market has a price for every ingredient yet.",
                         "مفيش محل عنده سعر لكل المكوّنات لسه.",
                         "Henüz hiçbir markette tüm malzemelerin fiyatı yok.",
                         "Hakuna duka lenye bei ya kila kiungo bado.",
                         "还没有商店为所有食材标价。",
                         "Пока ни в одном магазине нет цен на все ингредиенты."],
    "cmp.typeOwn":      ["Click any price to type your own.", "اضغط على أي سعر عشان تكتب سعرك.", "Kendi fiyatını yazmak için herhangi bir fiyata tıkla.", "Bofya bei yoyote kuandika yako.", "点击任意价格可自行输入。", "Нажмите на любую цену, чтобы ввести свою."],
    "cmp.startServer":  ["To fill them in automatically, start the price server.",
                         "عشان تتملا لوحدها، شغّل سيرفر الأسعار.",
                         "Otomatik dolması için fiyat sunucusunu başlat.",
                         "Ili zijazwe kiotomatiki, washa seva ya bei.",
                         "若要自动填充，请启动价格服务器。",
                         "Чтобы заполнить автоматически, запустите сервер цен."],
    "cmp.allFilled":    ["Every price is already filled in", "كل الأسعار متملية خلاص", "Tüm fiyatlar zaten dolu", "Bei zote tayari zimejazwa", "所有价格均已填写", "Все цены уже заполнены"],
    "cmp.lookingUp":    ["Looking up", "بيدوّر على", "Aranıyor", "Inatafuta", "正在查找", "Ищем"],
    "cmp.prices":       ["prices", "أسعار", "fiyat", "bei", "个价格", "цен"],
    "cmp.price":        ["price", "سعر", "fiyat", "bei", "个价格", "цену"],
    "cmp.filledIn":     ["Filled in", "اتملى", "Dolduruldu", "Imejazwa", "已填写", "Заполнено"],
    "cmp.noPriceFound": ["No price found", "ملقيناش سعر", "Fiyat bulunamadı", "Hakuna bei iliyopatikana", "未找到价格", "Цена не найдена"],
    "cmp.you":          ["you", "إنت", "sen", "wewe", "你", "вы"],
    "cmp.web":          ["web", "الويب", "web", "wavuti", "网络", "сеть"],
    "cmp.typedIn":      ["You typed this in", "إنت كتبته", "Bunu sen girdin", "Uliandika hii", "这是您输入的", "Вы ввели это"],
    "cmp.fetched":      ["Fetched automatically", "اتجاب لوحده", "Otomatik alındı", "Imepatikana kiotomatiki", "自动获取", "Получено автоматически"],
    "cmp.upTo":         ["up to", "لحد", "şu kadara kadar", "hadi", "最高", "до"],
    "cmp.clickEdit":    ["Click to edit", "اضغط للتعديل", "Düzenlemek için tıkla", "Bofya kuhariri", "点击编辑", "Нажмите, чтобы изменить"],
    "cmp.removePrice":  ["Remove price", "امسح السعر", "Fiyatı kaldır", "Ondoa bei", "移除价格", "Удалить цену"],

    # ---------------------------------------------------------------- game --
    "game.title":       ["Price Guess", "خمّن السعر", "Fiyat Tahmini", "Kisia Bei", "猜价格", "Угадай цену"],
    "game.which":       ["Which shop is cheaper?", "أنهي محل أرخص؟", "Hangi market daha ucuz?", "Duka lipi ni rahisi zaidi?", "哪家商店更便宜？", "Какой магазин дешевле?"],
    "game.score":       ["score", "النتيجة", "puan", "pointi", "得分", "счёт"],
    "game.streak":      ["streak", "متتالية", "seri", "mfululizo", "连胜", "серия"],
    "game.best":        ["best", "الأفضل", "en iyi", "bora", "最佳", "рекорд"],
    "game.whereCheaper": ["Where is it cheaper?", "فين أرخص؟", "Nerede daha ucuz?", "Wapi ni rahisi zaidi?", "哪里更便宜？", "Где дешевле?"],
    "game.right":       ["Right —", "صح —", "Doğru —", "Sahihi —", "正确 —", "Верно —"],
    "game.wrong":       ["Not quite —", "مش بالظبط —", "Tam değil —", "Si sahihi —", "不对 —", "Неверно —"],
    "game.cheaper":     ["cheaper.", "أرخص.", "daha ucuz.", "rahisi zaidi.", "更便宜。", "дешевле."],
    "game.samePrice":   ["Same price at both — that one’s free.", "نفس السعر في الاتنين — دي ببلاش.", "İkisinde de aynı fiyat — bu bedava.", "Bei sawa kwa zote mbili — hii ni bure.", "两边价格相同 — 这题算送的。", "Одинаковая цена — этот бесплатно."],
    "game.next":        ["Next round →", "الجولة الجاية →", "Sonraki tur →", "Raundi ijayo →", "下一轮 →", "Следующий раунд →"],
    "game.newBest":     ["New best score:", "رقم قياسي جديد:", "Yeni rekor:", "Rekodi mpya:", "新纪录：", "Новый рекорд:"],
    "game.practice":    ["These are practice prices. Once you’ve priced your own meals in Compare, the questions come from your real data.",
                         "دي أسعار تمرين. أول ما تسعّر وجباتك في المقارنة، الأسئلة هتيجي من بياناتك الحقيقية.",
                         "Bunlar alıştırma fiyatları. Kendi yemeklerini Karşılaştır’da fiyatlandırınca sorular gerçek verinden gelir.",
                         "Hizi ni bei za mazoezi. Ukishaweka bei za milo yako kwenye Linganisha, maswali yatatoka kwa data yako halisi.",
                         "这些是练习价格。在「比较」中为自己的餐食定价后，题目将来自您的真实数据。",
                         "Это тренировочные цены. Как только вы оцените свои блюда в «Сравнить», вопросы будут из ваших данных."],

    # ------------------------------------------------------------ settings --
    "set.whereShop":    ["Where you shop", "فين بتشتري", "Nerede alışveriş yapıyorsun", "Unanunua wapi", "您在哪里购物", "Где вы покупаете"],
    "set.yourArea":     ["Your area", "منطقتك", "Bölgen", "Eneo lako", "您的地区", "Ваш район"],
    "set.useLocation":  ["Use my location", "استخدم موقعي", "Konumumu kullan", "Tumia eneo langu", "使用我的位置", "Использовать моё местоположение"],
    "set.findMarkets":  ["Find markets near me", "دوّر على محلات قريبة", "Yakınımdaki marketleri bul", "Tafuta maduka karibu nami", "查找附近的商店", "Найти магазины рядом"],
    "set.markets":      ["Markets", "المحلات", "Marketler", "Maduka", "商店", "Магазины"],
    "set.marketPh":     ["Add a market, e.g. Kiler", "ضيف محل، مثلاً Kiler", "Market ekle, örn. Kiler", "Ongeza duka, mf. Kiler", "添加商店，例如 Kiler", "Добавить магазин, напр. Kiler"],
    "set.areaPh":       ["e.g. Gönyeli, Nicosia", "مثلاً Gönyeli, Nicosia", "örn. Gönyeli, Lefkoşa", "mf. Gönyeli, Nicosia", "例如 Gönyeli, Nicosia", "напр. Gönyeli, Nicosia"],
    "set.noMarkets":    ["No markets yet — add the shops you can actually get to.",
                         "مفيش محلات لسه — ضيف المحلات اللي فعلاً تقدر توصلها.",
                         "Henüz market yok — gerçekten gidebileceğin dükkânları ekle.",
                         "Bado hakuna maduka — ongeza maduka unayoweza kufika.",
                         "尚无商店 — 添加您实际能去的商店。",
                         "Магазинов пока нет — добавьте те, куда вы реально можете дойти."],
    "set.account":      ["Your account", "حسابك", "Hesabın", "Akaunti yako", "您的账户", "Ваш аккаунт"],
    "set.startOver":    ["Start over", "البدء من جديد", "Baştan başla", "Anza upya", "重新开始", "Начать заново"],
    "set.clearWarn":    ["Clearing removes every meal, price and market, and cannot be undone.",
                         "المسح بيشيل كل الوجبات والأسعار والمحلات، ومش هينفع ترجع فيه.",
                         "Temizlemek tüm yemekleri, fiyatları ve marketleri siler ve geri alınamaz.",
                         "Kufuta huondoa kila mlo, bei na duka, na hakuwezi kutenduliwa.",
                         "清除将删除所有餐食、价格和商店，且无法撤销。",
                         "Очистка удалит все блюда, цены и магазины — отменить нельзя."],
    "set.clearAll":     ["Clear all my data", "امسح كل بياناتي", "Tüm verilerimi sil", "Futa data yangu yote", "清除我的所有数据", "Удалить все мои данные"],
    "set.confirmClear": ["Delete every meal, price and market? This cannot be undone.",
                         "تمسح كل وجبة وسعر ومحل؟ مش هينفع ترجع فيها.",
                         "Tüm yemekler, fiyatlar ve marketler silinsin mi? Geri alınamaz.",
                         "Futa kila mlo, bei na duka? Hili haliwezi kutenduliwa.",
                         "删除所有餐食、价格和商店？此操作无法撤销。",
                         "Удалить все блюда, цены и магазины? Отменить нельзя."],
    "set.cleared":      ["Everything cleared", "اتمسح كل حاجة", "Her şey silindi", "Kila kitu kimefutwa", "已全部清除", "Всё удалено"],
    "set.finding":      ["Finding you…", "بيحدد مكانك…", "Konumun bulunuyor…", "Inakutafuta…", "正在定位…", "Определяем местоположение…"],
    "set.locationSet":  ["Location set from your device.", "المكان اتحدد من جهازك.", "Konum cihazından alındı.", "Eneo limewekwa kutoka kifaa chako.", "已从您的设备设置位置。", "Местоположение взято с вашего устройства."],
    "set.locationDenied": ["Location permission denied — type your area instead.",
                           "رفضت إذن الموقع — اكتب منطقتك بدلها.",
                           "Konum izni reddedildi — bölgeni yaz.",
                           "Ruhusa ya eneo imekataliwa — andika eneo lako.",
                           "位置权限被拒绝 — 请手动输入地区。",
                           "Доступ к геолокации запрещён — введите район вручную."],
    "set.noGeo":        ["This browser can’t share your location — type your area instead.",
                         "المتصفح ده مش بيشارك موقعك — اكتب منطقتك بدلها.",
                         "Bu tarayıcı konum paylaşamıyor — bölgeni yaz.",
                         "Kivinjari hiki hakiwezi kushiriki eneo lako — andika eneo lako.",
                         "此浏览器无法共享位置 — 请手动输入地区。",
                         "Этот браузер не передаёт местоположение — введите район вручную."],
    "set.typeArea":     ["Type your area first.", "اكتب منطقتك الأول.", "Önce bölgeni yaz.", "Andika eneo lako kwanza.", "请先输入您的地区。", "Сначала введите район."],
    "set.alreadyHave":  ["is already on the list", "موجود في القايمة خلاص", "zaten listede", "tayari yupo kwenye orodha", "已在列表中", "уже в списке"],
    "set.removed":      ["Removed", "اتشال", "Kaldırıldı", "Imeondolewa", "已移除", "Удалено"],
    "set.removeAsk":    ["and every price saved for it?", "وكل سعر محفوظ ليه؟", "ve ona kaydedilen tüm fiyatlar?", "na kila bei iliyohifadhiwa kwake?", "及为其保存的所有价格？", "и все сохранённые для него цены?"],
    "set.findWhy":      ["Finding shops automatically needs a Gemini key — paste one at the top of js/ai.js.",
                         "البحث الآلي عن المحلات محتاج مفتاح Gemini — حطّه فوق في js/ai.js.",
                         "Dükkânları otomatik bulmak için Gemini anahtarı gerekir — js/ai.js dosyasının başına yapıştır.",
                         "Kutafuta maduka kiotomatiki kunahitaji ufunguo wa Gemini — weka mmoja juu ya js/ai.js.",
                         "自动查找商店需要 Gemini 密钥 — 请粘贴到 js/ai.js 顶部。",
                         "Автопоиск магазинов требует ключ Gemini — вставьте его в начало js/ai.js."],
    "set.signedOut":    ["signed out", "خارج الحساب", "çıkış yapıldı", "umetoka", "已退出", "вы вышли"],
    "set.notSetUp":     ["not set up", "مش متظبط", "kurulmadı", "haijawekwa", "未设置", "не настроено"],
    "set.syncedState":  ["synced", "متزامن", "eşitlendi", "imesawazishwa", "已同步", "синхронизировано"],
    "set.savedHere":    ["Your meals are saved on this device. Sign in and they follow you to any other device you sign in on.",
                         "وجباتك محفوظة على الجهاز ده. سجّل دخول وهتمشي معاك على أي جهاز تاني تدخل منه.",
                         "Yemeklerin bu cihazda kayıtlı. Giriş yap, girdiğin her cihaza seninle gelsinler.",
                         "Milo yako yamehifadhiwa kwenye kifaa hiki. Ingia na yatakufuata kwenye kifaa chochote kingine.",
                         "您的餐食保存在本设备。登录后可在任何已登录的设备上查看。",
                         "Ваши блюда сохранены на этом устройстве. Войдите — и они будут на любом устройстве."],
    "set.signInCta":    ["Sign in or create an account", "سجّل دخول أو اعمل حساب", "Giriş yap veya hesap oluştur", "Ingia au fungua akaunti", "登录或创建账户", "Войти или создать аккаунт"],
    "set.signedInAs":   ["Signed in as", "مسجّل دخول كـ", "Giriş yapan", "Umeingia kama", "登录为", "Вы вошли как"],
    "set.howSync":      ["Changes are saved here first, then copied to your account a moment later — so it stays quick, and keeps working with no internet.",
                         "التغييرات بتتحفظ هنا الأول، وبعدها بلحظة بتتنسخ لحسابك — عشان يفضل سريع، ويشتغل من غير نت.",
                         "Değişiklikler önce burada kaydedilir, biraz sonra hesabına kopyalanır — hızlı kalır ve internetsiz de çalışır.",
                         "Mabadiliko huhifadhiwa hapa kwanza, kisha hunakiliwa kwenye akaunti yako baadaye — hivyo inabaki haraka na hufanya kazi bila mtandao.",
                         "更改先保存在本地，稍后再同步到您的账户 — 既快速又可离线使用。",
                         "Изменения сохраняются сначала здесь, затем копируются в аккаунт — быстро и работает без интернета."],
    "set.clearCloudNote": ["Clearing removes every meal, price and market from this device. Your account copy is replaced the next time this device saves.",
                           "المسح بيشيل كل الوجبات والأسعار والمحلات من الجهاز ده. والنسخة اللي في حسابك هتتبدل أول ما الجهاز ده يحفظ.",
                           "Temizlemek bu cihazdaki tüm yemekleri, fiyatları ve marketleri siler. Hesabındaki kopya bu cihaz bir dahaki kaydettiğinde değişir.",
                           "Kufuta huondoa kila mlo, bei na duka kutoka kifaa hiki. Nakala ya akaunti yako hubadilishwa kifaa hiki kitakapohifadhi tena.",
                           "清除将从本设备删除所有餐食、价格和商店。下次本设备保存时将覆盖账户中的副本。",
                           "Очистка удалит все блюда, цены и магазины с этого устройства. Копия в аккаунте заменится при следующем сохранении."],
    "set.syncNow":      ["Sync now", "زامن دلوقتي", "Şimdi eşitle", "Sawazisha sasa", "立即同步", "Синхронизировать"],
    "set.upToDate":     ["Up to date", "محدّث", "Güncel", "Ni ya kisasa", "已是最新", "Актуально"],

    # ----------------------------------------------------------------- login --
    "log.signIn":       ["Sign in", "تسجيل الدخول", "Giriş yap", "Ingia", "登录", "Войти"],
    "log.createAcc":    ["Create an account", "إنشاء حساب", "Hesap oluştur", "Fungua akaunti", "创建账户", "Создать аккаунт"],
    "log.welcome":      ["Welcome back. Your list is waiting.", "أهلاً بعودتك. قايمتك مستنياك.", "Tekrar hoş geldin. Listen seni bekliyor.", "Karibu tena. Orodha yako inakusubiri.", "欢迎回来，您的清单在等您。", "С возвращением. Ваш список ждёт."],
    "log.email":        ["Email", "الإيميل", "E-posta", "Barua pepe", "邮箱", "Эл. почта"],
    "log.password":     ["Password", "كلمة السر", "Şifre", "Nenosiri", "密码", "Пароль"],
    "log.noAccount":    ["No account yet?", "لسه مفيش حساب؟", "Hesabın yok mu?", "Bado huna akaunti?", "还没有账户？", "Ещё нет аккаунта?"],
    "log.createOne":    ["Create one", "اعمل واحد", "Bir tane oluştur", "Fungua moja", "创建一个", "Создать"],
    "log.haveAccount":  ["Already have one?", "عندك حساب خلاص؟", "Zaten var mı?", "Tayari unayo?", "已有账户？", "Уже есть аккаунт?"],
    "log.signInInstead": ["Sign in instead", "سجّل دخول بدلها", "Bunun yerine giriş yap", "Ingia badala yake", "改为登录", "Войти вместо этого"],
    "log.withoutAcc":   ["You can also just use it without an account — everything stays on this device.",
                         "تقدر كمان تستعمله من غير حساب — كل حاجة هتفضل على الجهاز ده.",
                         "Hesapsız da kullanabilirsin — her şey bu cihazda kalır.",
                         "Unaweza pia kuitumia bila akaunti — kila kitu kinabaki kwenye kifaa hiki.",
                         "您也可以不注册直接使用 — 所有内容保存在本设备。",
                         "Можно пользоваться и без аккаунта — всё останется на этом устройстве."],
}

LANGS = [
    {"code": "en", "label": "English",  "dir": "ltr"},
    {"code": "ar", "label": "العربية",  "dir": "rtl"},
    {"code": "tr", "label": "Türkçe",   "dir": "ltr"},
    {"code": "sw", "label": "Kiswahili", "dir": "ltr"},
    {"code": "zh", "label": "中文",      "dir": "ltr"},
    {"code": "ru", "label": "Русский",  "dir": "ltr"},
]

ORDER = [l["code"] for l in LANGS]

# نقلب القاموس: لغة → {مفتاح: نص}
by_lang = {code: {} for code in ORDER}
for key, values in D.items():
    if len(values) != len(ORDER):
        raise SystemExit(f'{key}: {len(values)} ترجمة، المفروض {len(ORDER)}')
    for code, text in zip(ORDER, values):
        by_lang[code][key] = text

header = '''/* ===========================================================================
   i18n.js — الترجمة.

   مُولَّد من make_i18n.py. ما تعدّلوش بإيدك — عدّل القاموس هناك وأعد
   التوليد، وإلا أول تحديث هيمسح شغلك.

   الاستعمال:
     T('nav.meals')              النص باللغة الحالية
     <span data-i18n="nav.meals"></span>     بيتملا لوحده
     <input data-i18n-ph="meals.qty">        الـ placeholder

   بيتحمّل قبل أي ملف تاني، عشان الصفحات تلاقي T جاهزة.
   =========================================================================== */

var I18N = (function () {
  'use strict';

  var STORE = 'basket-lang';

  var LANGS = %LANGS%;

  var DICT = %DICT%;

  /**
   * اللغة الحالية. بنقراها مرة ونخزّنها في متغير — دي بتتنادى
   * مئات المرات في كل رسم، وقراءة localStorage كل مرة إهدار.
   */
  var current = (function () {
    try {
      var saved = localStorage.getItem(STORE);
      if (saved && DICT[saved]) return saved;
    } catch (e) { /* نافذة خاصة */ }

    // لغة المتصفح لو إحنا بنعرفها، وإلا إنجليزي.
    var guess = (navigator.language || 'en').slice(0, 2).toLowerCase();
    return DICT[guess] ? guess : 'en';
  })();

  function lang() { return current; }

  function dir() {
    for (var i = 0; i < LANGS.length; i++) {
      if (LANGS[i].code === current) return LANGS[i].dir;
    }
    return 'ltr';
  }

  /**
   * النص. لو المفتاح مش موجود في اللغة دي، بنرجع للإنجليزي بدل
   * ما نعرض المفتاح نفسه — ترجمة ناقصة أحسن من "cmp.addPrice"
   * ظاهرة لليوزر.
   */
  function t(key) {
    var table = DICT[current] || DICT.en;
    if (table && table[key] != null) return table[key];
    if (DICT.en && DICT.en[key] != null) return DICT.en[key];
    return key;
  }

  function set(code) {
    if (!DICT[code] || code === current) return;
    current = code;
    try { localStorage.setItem(STORE, code); } catch (e) { /* تجاهل */ }
    // إعادة تحميل أبسط وأأمن من إننا نعيد رسم كل صفحة بإيدنا —
    // النصوص موجودة في عشرات الأماكن، وأي واحد ننساه هيفضل بلغة قديمة.
    location.reload();
  }

  /** بيملا كل عنصر عليه data-i18n أو data-i18n-ph. */
  function apply(root) {
    var scope = root || document;

    scope.querySelectorAll('[data-i18n]').forEach(function (el) {
      el.textContent = t(el.getAttribute('data-i18n'));
    });

    scope.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-ph')));
    });

    scope.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
  }

  // اتجاه الصفحة ولغتها لازم يتظبطوا بدري، قبل أول رسم —
  // وإلا الصفحة هتترسم شمال-يمين وبعدين تتقلب قدام اليوزر.
  document.documentElement.setAttribute('lang', current);
  document.documentElement.setAttribute('dir', dir());

  return { t: t, lang: lang, set: set, dir: dir, apply: apply, LANGS: LANGS };
})();

/* اختصار. بتتنادى كتير أوي عشان تفضل I18N.t في كل مرة. */
function T(key) { return I18N.t(key); }
'''

js = (header
      .replace('%LANGS%', json.dumps(LANGS, ensure_ascii=False, indent=4).replace('\n', '\n  '))
      .replace('%DICT%', json.dumps(by_lang, ensure_ascii=False, indent=4).replace('\n', '\n  ')))

out = pathlib.Path('/home/claude/build/i18n.js')
out.write_text(js, encoding='utf-8')
print(f'{len(D)} مفتاح × {len(ORDER)} لغات = {len(D)*len(ORDER)} ترجمة')
print('->', out, f'{out.stat().st_size // 1024} KB')
