import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup,
                            ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, PhotoSize)
from aiogram.fsm.storage.memory import MemoryStorage

# полученный у @BotFather
BOT_TOKEN = ''

# Инициализируем хранилище (создаем экземпляр класса MemoryStorage)
storage = MemoryStorage()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

# Объект бота
bot = Bot(token=BOT_TOKEN)
# Диспетчер
dp = Dispatcher(storage=storage)

# # Создаем "базу данных" пользователей
user_dict: dict[int, dict[str, str | int | bool]] = {}

# Cоздаем класс, наследуемый от StatesGroup, для группы состояний нашей FSM
class FSMFillForm(StatesGroup):
    # Создаем экземпляры класса State, последовательно
    # перечисляя возможные состояния, в которых будет находиться
    # бот в разные моменты взаимодействия с пользователем
    files = State()        # Состояние ожидания ввода изображений
    fio = State()         # Состояние ожидания ввода fio
    gender = State()      # Состояние ожидания выбора пола
    promt= State()     # Состояние ожидания загрузки текста

# Функция для настройки кнопки Menu бота
async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(
            command='/start',
            description='Начать'),
    ]
    await bot.set_my_commands(main_menu_commands)


# Хэндлер на команду /start
@dp.message(CommandStart(), StateFilter(default_state))
async def cmd_start(message: types.Message):
    # Создаем объекты кнопок
    button_1 = KeyboardButton(text='ControlNet')
    button_2 = KeyboardButton(text='Lora_train')
    button_3 = KeyboardButton(text='Lora_inference')

    # Создаем объект клавиатуры, добавляя в него кнопки
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[button_1, button_2, button_3]],
        resize_keyboard=True
    )

    await message.answer(
        text = "Привет! Я - бот, который умеет обучать ControlNet и LoRA на твоих данных",
        reply_markup=keyboard
    )
   

# Этот хэндлер будет срабатывать на команду "/cancel" в любых состояниях,
# кроме состояния по умолчанию, и отключать машину состояний
@dp.message(Command(commands='cancel'), ~StateFilter(default_state))
async def process_cancel_command_state(message: Message, state: FSMContext):
    await message.answer(
        text='Вы вышли из команды\n\n'
             'Чтобы снова перейти к заполнению данных - '
             'отправьте команду /start'
    )
    # Сбрасываем состояние и очищаем данные, полученные внутри состояний
    await state.clear()

#-----------------------------------------------------------------------------------------
# Этот хэндлер будет срабатывать на ответ "ControlNet" 
@dp.message(F.text == 'ControlNet', StateFilter(default_state))
async def process_ControlNet_answer(message: Message, state: FSMContext):
    await message.answer(
        text='Введите ваше fio',
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(FSMFillForm.fio)


# Этот хэндлер будет срабатывать, если введен корректный fio
# и переводить в состояние выбора пола
@dp.message(StateFilter(FSMFillForm.fio))
async def process_fio_sent(message: Message, state: FSMContext):
    # Cохраняем имя в хранилище по ключу "fio"
    await state.update_data(fio=message.text)
    # Создаем объекты инлайн-кнопок
    male_button = InlineKeyboardButton(
        text='women',
        callback_data='women'
    )
    female_button = InlineKeyboardButton(
        text='men',
             callback_data='men'
    )

    # Добавляем кнопки в клавиатуру (две в одном ряду )
    keyboard: list[list[InlineKeyboardButton]] = [
        [male_button, female_button]
    ]
    # Создаем объект инлайн-клавиатуры
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    # Отправляем пользователю сообщение с клавиатурой
    await message.answer(
        text='Спасибо!\n\nУкажите ваш пол',
        reply_markup=markup
    )
    # Устанавливаем состояние ожидания выбора пола
    await state.set_state(FSMFillForm.gender)

# Этот хэндлер будет срабатывать на нажатие кнопки при
# выборе пола и переводить в состояние отправки фото
@dp.callback_query(StateFilter(FSMFillForm.gender),
                   F.data.in_(['women', 'men']))
async def process_gender_press(callback: CallbackQuery, state: FSMContext):
    # Cохраняем пол (callback.data нажатой кнопки) в хранилище,
    # по ключу "gender"
    await state.update_data(gender=callback.data)
    # Удаляем сообщение с кнопками, потому что следующий этап - загрузка фото
    # чтобы у пользователя не было желания тыкать кнопки
    await callback.message.delete()
    await callback.message.answer(
        text='Спасибо! А теперь загрузите, пожалуйста, фото'
    )
    # Устанавливаем состояние ожидания загрузки фото
    await state.set_state(FSMFillForm.files)


# Этот хэндлер будет срабатывать, если во время выбора пола
# будет введено/отправлено что-то некорректное
@dp.message(StateFilter(FSMFillForm.gender))
async def warning_not_gender(message: Message):
    await message.answer(
        text='Пожалуйста, пользуйтесь кнопками '
             'при выборе пола\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


# Этот хэндлер будет срабатывать, если отправлено фото
# и переводить в состояние ввода promt
@dp.message(StateFilter(FSMFillForm.files),
            F.photo[-1].as_('largest_photo'))
async def process_photo_sent(message: Message,
                             state: FSMContext,
                             largest_photo: PhotoSize):
    # Cохраняем данные фото (file_unique_id и file_id) в хранилище
    # по ключам "photo_unique_id" и "photo_id"
    await state.update_data(
        photo_unique_id=largest_photo.file_unique_id,
        photo_id=largest_photo.file_id
    )
    await message.answer(
        text='Введите свой promt',
        reply_markup=ReplyKeyboardRemove()
    )
    # Устанавливаем состояние ожидания выбора образования
    await state.set_state(FSMFillForm.promt)


# Этот хэндлер будет срабатывать, если во время отправки фото
# будет введено/отправлено что-то некорректное
@dp.message(StateFilter(FSMFillForm.files))
async def warning_not_photo(message: Message):
    await message.answer(
        text='Пожалуйста, на этом шаге отправьте '
             'ваше фото\n\nЕсли вы хотите прервать '
             'заполнение анкеты - отправьте команду /cancel'
    )


# Этот хэндлер будет срабатывать на ввод promt
# выводить из машины состояний
@dp.message(StateFilter(FSMFillForm.promt), F.text.isalpha())
async def process_promt_sent(message: Message, state: FSMContext):
    # Cохраняем имя в хранилище по ключу "promt"
    await state.update_data(promt=message.text)
    # Добавляем в "базу данных" анкету пользователя
    # по ключу id пользователя
    user_dict[message.from_user.id] = await state.get_data()
    # Завершаем машину состояний
    await state.clear()
    # Отправляем в чат сообщение о выходе из машины состояний
    await message.answer(
        text='Спасибо! Ваши данные сохранены!\n\n'
    )


# Этот хэндлер будет срабатывать, если во время отправки Promt
# будет введено/отправлено что-то некорректное
@dp.message(StateFilter(FSMFillForm.promt))
async def warning_not_promt(message: Message):
    await message.answer(
        text='Пожалуйста, напишите корректный promt!\n\n'
             'Если вы хотите прервать заполнение анкеты - '
             'отправьте команду /cancel'
    )
#--------------------------------------------------------------------------------------------------------------    
# Этот хэндлер будет срабатывать на любые сообщения в состоянии "по умолчанию",
# кроме тех, для которых есть отдельные хэндлеры
@dp.message(StateFilter(default_state))
async def send_echo(message: Message):
    await message.reply(text='Извините, не понимаю')

# @dp.message(StateFilter(default_state))
# async def process_sent(message: Message):
#     print(await message.get_data())
#     print(await message.get_state())


# Запуск процесса поллинга новых апдейтов
async def main():
    await set_main_menu(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


print(user_dict)

