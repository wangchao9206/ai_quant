import datetime
import math

class YiJingEngine:
    """
    易经核心推演引擎
    结合象数理模型与现代金融数据，提供市场预测与投资智慧。
    """

    # 八卦基础属性 (乾兑离震巽坎艮坤)
    # 二进制: 1=阳, 0=阴 (自下而上)
    TRIGRAMS = {
        "111": {"name": "乾", "nature": "天", "element": "金", "direction": "西北"},
        "011": {"name": "兑", "nature": "泽", "element": "金", "direction": "西"},
        "101": {"name": "离", "nature": "火", "element": "火", "direction": "南"},
        "001": {"name": "震", "nature": "雷", "element": "木", "direction": "东"},
        "110": {"name": "巽", "nature": "风", "element": "木", "direction": "东南"},
        "010": {"name": "坎", "nature": "水", "element": "水", "direction": "北"},
        "100": {"name": "艮", "nature": "山", "element": "土", "direction": "东北"},
        "000": {"name": "坤", "nature": "地", "element": "土", "direction": "西南"},
    }

    # 六十四卦投资解读 (精简版，覆盖常见卦象)
    HEXAGRAMS_DATA = {
        "111111": {"name": "乾为天", "trend": "强多头", "advice": "潜龙勿用至飞龙在天，趋势确立，持股待涨，但需警惕亢龙有悔。", "meaning": "刚健中正，大吉大利"},
        "000000": {"name": "坤为地", "trend": "空头/筑底", "advice": "厚德载物，市场处于积累期，宜静观其变，顺势而为。", "meaning": "柔顺伸展，利于西南"},
        "010001": {"name": "水雷屯", "trend": "震荡/初创", "advice": "万事开头难，市场方向不明，波动剧烈，宜轻仓试探。", "meaning": "云雷屯，君子以经纶"},
        "100010": {"name": "山水蒙", "trend": "迷茫/调整", "advice": "前景蒙昧不明，主力洗盘，不宜盲目加仓，待云开雾散。", "meaning": "山下出泉，君子以果行育德"},
        "010111": {"name": "水天需", "trend": "等待", "advice": "密云不雨，时机未到，耐心等待突破信号。", "meaning": "云上于天，君子以饮食宴乐"},
        "111010": {"name": "天水讼", "trend": "分歧", "advice": "多空分歧巨大，争执不下，注意风险控制，避免追高。", "meaning": "天与水违，君子以作事谋始"},
        "000010": {"name": "地水师", "trend": "震荡下行", "advice": "行险而顺，市场风险聚集，需有严明的纪律(止损)。", "meaning": "地中有水，君子以容民畜众"},
        "010000": {"name": "水地比", "trend": "合作/跟随", "advice": "众星捧月，跟随龙头板块，与趋势为友。", "meaning": "地上有水，君子以建万国亲诸侯"},
        "110111": {"name": "风天小畜", "trend": "小幅盘整", "advice": "密云不雨，蓄势待发，短期获利空间有限，积小胜为大胜。", "meaning": "风行天上，君子以懿文德"},
        "111011": {"name": "天泽履", "trend": "谨慎上行", "advice": "如履薄冰，虽有上涨趋势，但需步步为营，谨防踏空或踩雷。", "meaning": "上天下泽，君子以辨上下定民志"},
        "000111": {"name": "地天泰", "trend": "大牛市", "advice": "天地交而万物通，阴阳平衡，最佳盈利时期，积极参与。", "meaning": "天地交，君子以财成天地之道"},
        "111000": {"name": "天地否", "trend": "熊市", "advice": "天地不交，万物不通，市场流动性枯竭，宜空仓避险。", "meaning": "天地不交，君子以俭德辟难"},
        "101111": {"name": "天火同人", "trend": "普涨", "advice": "上下同欲，板块轮动健康，可广泛布局。", "meaning": "天与火，君子以类族辨物"},
        "111101": {"name": "火天大有", "trend": "主升浪", "advice": "火在天上，普照万物，行情火爆，收获季节。", "meaning": "火在天上，君子以遏恶扬善"},
        "000100": {"name": "地山谦", "trend": "回调", "advice": "满招损，谦受益，市场冲高回落，获利了结为宜。", "meaning": "地中有山，君子以裒多益寡"},
        "001000": {"name": "雷地豫", "trend": "反弹", "advice": "雷出地奋，市场超跌反弹，由于势头迅猛，可短线参与。", "meaning": "雷出地奋，君子以作乐崇德"},
        "011001": {"name": "泽雷随", "trend": "顺势", "advice": "随时变通，不要固执己见，跟随市场热点切换。", "meaning": "泽中有雷，君子以向晦入宴息"},
        "100110": {"name": "山风蛊", "trend": "崩盘/黑天鹅", "advice": "物腐虫生，市场基本面恶化，需刮骨疗毒，彻底出清。", "meaning": "山下有风，君子以振民育德"},
        "000011": {"name": "地泽临", "trend": "探底回升", "advice": "泽上有地，利好逐步兑现，上升通道打开。", "meaning": "泽上有地，君子以教思无穷"},
        "110000": {"name": "风地观", "trend": "观望", "advice": "风行地上，万物静观，看不懂行情时最好的操作是休息。", "meaning": "风行地上，君子以省方观民设教"},
        "101001": {"name": "火雷噬嗑", "trend": "突破", "advice": "咬碎硬骨头，突破关键压力位，需放量攻击。", "meaning": "雷电，君子以明罚敕法"},
        "100101": {"name": "山火贲", "trend": "虚高/泡沫", "advice": "文饰外观，金玉其外，注意题材炒作退潮风险。", "meaning": "山下有火，君子以明庶政"},
        "100000": {"name": "山地剥", "trend": "暴跌", "advice": "山附于地，阴盛阳衰，主力出货，君子不立危墙之下。", "meaning": "山附于地，上以厚下安宅"},
        "000001": {"name": "地雷复", "trend": "触底反弹", "advice": "一阳来复，至暗时刻已过，抄底良机。", "meaning": "雷在地中，君子以此时着至日闭关"},
        "111001": {"name": "天雷无妄", "trend": "意外", "advice": "不妄动，市场充满不确定性，切勿听信小道消息。", "meaning": "天下雷行，君子以茂对时育万物"},
        "100111": {"name": "山天大畜", "trend": "长牛蓄势", "advice": "刚健笃实，辉光日新，长期投资价值凸显。", "meaning": "天在山中，君子以多识前言往行"},
        "100001": {"name": "山雷颐", "trend": "盘整", "advice": "慎言语，节饮食，休养生息，关注防御性板块。", "meaning": "山下有雷，君子以慎言语节饮食"},
        "011110": {"name": "泽风大过", "trend": "严重超买", "advice": "栋桡，压力过大，随时可能发生踩踏，极度危险。", "meaning": "泽灭木，君子以独立不惧"},
        "010010": {"name": "坎为水", "trend": "深跌", "advice": "水流而不盈，行险而不失其信，市场极度低迷，信心崩溃。", "meaning": "水洊至，君子以常德行"},
        "101101": {"name": "离为火", "trend": "暴涨", "advice": "日月丽乎天，行情如火如荼，注意物极必反。", "meaning": "明两作，君子以继明照于四方"},
        "001110": {"name": "泽山咸", "trend": "敏感/感应", "advice": "心有灵犀，市场对消息面极度敏感，快进快出。", "meaning": "山上有泽，君子以虚受人"},
        "011100": {"name": "雷风恒", "trend": "慢牛", "advice": "雷风相与，立不易方，坚持长期主义，持有核心资产。", "meaning": "雷风，君子以立不易方"},
        "111100": {"name": "天山遁", "trend": "退潮", "advice": "好汉不吃眼前亏，获利盘涌出，及时撤退。", "meaning": "天下有山，君子以远小人"},
        "001111": {"name": "雷天大壮", "trend": "强势突破", "advice": "雷在天上，声势浩大，行情加速赶顶，注意止盈。", "meaning": "雷在天上，君子以非礼弗履"},
        "101000": {"name": "火地晋", "trend": "旭日东升", "advice": "明出地上，顺风顺水，加仓持有。", "meaning": "明出地上，君子以自昭明德"},
        "000101": {"name": "地火明夷", "trend": "至暗时刻", "advice": "明入地中，利空不断，宜韬光养晦，等待黎明。", "meaning": "明入地中，君子以莅众用晦"},
        "110101": {"name": "风火家人", "trend": "内循环", "advice": "言有物，行有恒，关注内需消费板块。", "meaning": "风自火出，君子以言有物而行有恒"},
        "101011": {"name": "火泽睽", "trend": "背离", "advice": "二女同居，其志不同，量价背离，谨防诱多。", "meaning": "上火下泽，君子以同而异"},
        "010100": {"name": "水山蹇", "trend": "受阻", "advice": "山高水深，寸步难行，外部环境恶劣，停止操作。", "meaning": "山上有水，君子以反身修德"},
        "001010": {"name": "雷水解", "trend": "解套", "advice": "雷雨作，风险释放完毕，利空出尽是利好。", "meaning": "雷雨作，君子以赦过宥罪"},
        "100011": {"name": "山泽损", "trend": "割肉", "advice": "损下益上，不得不止损离场，保留本金。", "meaning": "山下有泽，君子以惩忿窒欲"},
        "110001": {"name": "风雷益", "trend": "获利", "advice": "风雷激荡，市场活跃，积极进取，利润丰厚。", "meaning": "风雷，君子以见善则迁"},
        "011111": {"name": "泽天夬", "trend": "决断/顶部", "advice": "扬于王庭，高位震荡，必须果断卖出，不再留恋。", "meaning": "泽上于天，君子以施禄及下"},
        "111110": {"name": "天风姤", "trend": "遇合/阴跌", "advice": "天下有风，阴气初生，不宜长线持有，警惕温水煮青蛙。", "meaning": "天下有风，后以施命诰四方"},
        "001000": {"name": "泽地萃", "trend": "聚集", "advice": "泽上于地，资金抱团，关注核心赛道龙头。", "meaning": "泽上于地，君子以除戎器戒不虞"},
        "000110": {"name": "地风升", "trend": "稳步上涨", "advice": "地中生木，积少成多，适合定投和长线布局。", "meaning": "地中生木，君子以顺德积小以高大"},
        "011010": {"name": "困", "trend": "困境", "advice": "泽无水，流动性枯竭，无量阴跌，最为煎熬。", "meaning": "泽无水，君子以致命遂志"},
        "010110": {"name": "井", "trend": "价值洼地", "advice": "木上有水，价值回归，挖掘低估值蓝筹。", "meaning": "木上有水，君子以劳民劝相"},
        "011101": {"name": "泽火革", "trend": "变革/变盘", "advice": "泽中有火，市场风格大切换，需及时调仓换股。", "meaning": "泽中有火，君子以治历明时"},
        "101110": {"name": "火风鼎", "trend": "确立/稳固", "advice": "木上有火，行情稳固，可重仓持有。", "meaning": "木上有火，君子以正位凝命"},
        "001001": {"name": "震为雷", "trend": "剧烈震荡", "advice": "震惊百里，消息面重磅炸弹，多看少动，恐慌中找机会。", "meaning": "这也是震，君子以恐惧修省"},
        "100100": {"name": "艮为山", "trend": "止跌/横盘", "advice": "兼山，动静不失其时，市场进入静默期，管住手。", "meaning": "兼山，君子以思不出其位"},
        "110100": {"name": "风山渐", "trend": "循序渐进", "advice": "山上有木，慢牛格局，切勿急躁，持股待涨。", "meaning": "山上有木，君子以居贤德善俗"},
        "001011": {"name": "雷泽归妹", "trend": "错配/动荡", "advice": "泽上有雷，市场结构扭曲，短线投机盛行，注意风险。", "meaning": "泽上有雷，君子以永终知敝"},
        "001101": {"name": "雷火丰", "trend": "繁荣顶点", "advice": "雷电皆至，烈火烹油，最辉煌时往往也是最危险时。", "meaning": "雷电皆至，君子以折狱致刑"},
        "101100": {"name": "火山旅", "trend": "不稳定", "advice": "山上有火，游资主导，快进快出，不可恋战。", "meaning": "山上有火，君子以明慎用刑"},
        "110110": {"name": "巽为风", "trend": "波动/消息", "advice": "随风而入，市场随消息面起舞，无主见，顺势操作。", "meaning": "随风，君子以申命行事"},
        "011011": {"name": "兑为泽", "trend": "喜悦/反弹", "advice": "丽泽，市场情绪高涨，交投活跃，享受泡沫。", "meaning": "丽泽，君子以朋友讲习"},
        "110010": {"name": "风水涣", "trend": "涣散", "advice": "风行水上，人心思变，资金出逃，行情瓦解。", "meaning": "风行水上，先王以享于帝立庙"},
        "010011": {"name": "水泽节", "trend": "节制", "advice": "泽上有水，适可而止，控制仓位，不要贪婪。", "meaning": "泽上有水，君子以制数度议德行"},
        "110011": {"name": "风泽中孚", "trend": "诚信/回归", "advice": "泽上有风，价值回归，相信常识，回归基本面。", "meaning": "泽上有风，君子以议狱缓死"},
        "001100": {"name": "雷山小过", "trend": "矫枉过正", "advice": "山上有雷，市场反应过度，存在超跌反弹或超买回调机会。", "meaning": "山上有雷，君子以行过乎恭"},
        "010101": {"name": "水火既济", "trend": "完美/见顶", "advice": "水在火上，功德圆满，利好兑现，行情结束。", "meaning": "水在火上，君子以思患而预防之"},
        "101010": {"name": "火水未济", "trend": "未完成/希望", "advice": "火在水上，新的周期正在孕育，黎明前的黑暗。", "meaning": "火在水上，君子以慎辨物居方"},
    }

    def _get_trigram(self, val):
        """根据数值获取八卦 (取余数)"""
        # 乾1 兑2 离3 震4 巽5 坎6 艮7 坤8
        # 注意: 这里的数字对应先天八卦数或后天八卦数，这里采用简单的取模对应
        # 1=乾, 2=兑, 3=离, 4=震, 5=巽, 6=坎, 7=艮, 0=坤
        idx = val % 8
        map_code = {
            1: "111", # 乾
            2: "011", # 兑
            3: "101", # 离
            4: "001", # 震
            5: "110", # 巽
            6: "010", # 坎
            7: "100", # 艮
            0: "000", # 坤
        }
        return map_code[idx]

    def get_forecast(self, seed_value: float, additional_factor: int = 0):
        """
        梅花易数起卦法 (数字起卦)
        seed_value: 通常是价格、时间戳等
        additional_factor: 比如涨跌幅，用于动爻
        """
        # 提取整数部分和小数部分处理
        total = int(seed_value * 100) + additional_factor
        
        # 上卦: (总数) % 8
        upper_code = self._get_trigram(total)
        
        # 下卦: (总数 + 时间因子) % 8
        # 使用当前小时作为变量
        now_hour = datetime.datetime.now().hour
        lower_code = self._get_trigram(total + now_hour)
        
        # 组合成六十四卦 (Top-to-Bottom string)
        # 上卦在前，下卦在后
        hex_key = upper_code + lower_code
        
        # 动爻: (总数 + 时间) % 6
        # 1-based index (1=Bottom, 6=Top)
        moving_line_idx = (total + now_hour) % 6
        if moving_line_idx == 0:
            moving_line_idx = 6
            
        hex_data = self.HEXAGRAMS_DATA.get(hex_key)
        
        if not hex_data:
            # Fallback (理论上不应发生，除非字典不全)
            hex_data = {"name": "未知", "trend": "不明", "advice": "静观其变", "meaning": "未知"}

        # 变卦 (变动爻后的卦)
        # 字符串是 Top-to-Bottom
        # moving_line_idx 1 (Bottom) -> index 5
        # moving_line_idx 6 (Top) -> index 0
        bits = list(hex_key)
        target_idx = 6 - moving_line_idx
        
        original_bit = bits[target_idx]
        bits[target_idx] = '0' if original_bit == '1' else '1'
        new_hex_key = "".join(bits)
        
        new_hex_data = self.HEXAGRAMS_DATA.get(new_hex_key, {"name": "未知", "trend": "不明"})
        
        # 奇门时空 (简化版: 根据小时判断方位吉凶)
        auspicious_direction, lucky_time = self._qimen_dunjia(now_hour)

        return {
            "hexagram": {
                "code": hex_key, # 二进制码 (下->上)
                "name": hex_data["name"],
                "trend": hex_data["trend"],
                "advice": hex_data["advice"],
                "meaning": hex_data["meaning"],
                "upper_trigram": self._get_trigram_name(upper_code),
                "lower_trigram": self._get_trigram_name(lower_code)
            },
            "moving_line": moving_line_idx,
            "future_hexagram": {
                "code": new_hex_key,
                "name": new_hex_data["name"],
                "trend": new_hex_data["trend"]
            },
            "qimen": {
                "auspicious_direction": auspicious_direction,
                "lucky_time": lucky_time,
                "current_element": self._get_hour_element(now_hour)
            }
        }

    def _get_trigram_name(self, code):
        return self.TRIGRAMS.get(code, {}).get("nature", "")

    def _qimen_dunjia(self, hour):
        """简化的奇门时空判断"""
        # 子午流注/时辰吉凶
        # 简单映射
        time_map = {
            "23-1": ("正北", "生门旺"), # 子
            "1-3": ("东北", "休门旺"), # 丑
            "3-5": ("东北", "生门旺"), # 寅
            "5-7": ("正东", "伤门(强势)"), # 卯
            "7-9": ("东南", "杜门(潜伏)"), # 辰
            "9-11": ("东南", "景门(活跃)"), # 巳
            "11-13": ("正南", "景门旺"), # 午
            "13-15": ("西南", "死门(调整)"), # 未
            "15-17": ("西南", "惊门(波动)"), # 申
            "17-19": ("正西", "开门(收获)"), # 酉
            "19-21": ("西北", "开门旺"), # 戌
            "21-23": ("西北", "休门(休息)")  # 亥
        }
        
        # Determine slot
        h = hour
        slot = ""
        if h >= 23 or h < 1: slot = "23-1"
        elif 1 <= h < 3: slot = "1-3"
        elif 3 <= h < 5: slot = "3-5"
        elif 5 <= h < 7: slot = "5-7"
        elif 7 <= h < 9: slot = "7-9"
        elif 9 <= h < 11: slot = "9-11"
        elif 11 <= h < 13: slot = "11-13"
        elif 13 <= h < 15: slot = "13-15"
        elif 15 <= h < 17: slot = "15-17"
        elif 17 <= h < 19: slot = "17-19"
        elif 19 <= h < 21: slot = "19-21"
        elif 21 <= h < 23: slot = "21-23"
        
        return time_map.get(slot, ("中宫", "平"))

    def _get_hour_element(self, hour):
        # 简易五行
        if hour in [23, 0, 1, 21, 22]: return "水" # 亥子
        if hour in [2, 3, 4, 5]: return "木" # 寅卯
        if hour in [8, 9, 10, 11, 12, 13]: return "火" # 巳午
        if hour in [14, 15, 16, 17]: return "金" # 申酉
        return "土" # 辰戌丑未 (7-8, 13-14, 19-20, 1-2 approx) - simplified
