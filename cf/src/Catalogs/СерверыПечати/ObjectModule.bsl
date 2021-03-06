// @strict-types

#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда

#Область ОбработчикиСобытий
	
Процедура ПередЗаписью(Отказ)
	
	Если ОбменДанными.Загрузка = Истина Тогда
		Возврат;
	КонецЕсли;
	
	Если НЕ ЗначениеЗаполнено(Наименование) Тогда
		ДанныеЗаполнения = Новый Структура;
		ДанныеЗаполнения.Вставить("Сервер", Сервер);
		ДанныеЗаполнения.Вставить("Порт", Порт);
		Наименование = Справочники.СерверыПечати.ПолучитьНаименованиеПоШаблону(ДанныеЗаполнения);
	КонецЕсли;
	
КонецПроцедуры

#КонецОбласти


#КонецЕсли
