from faker import Faker
fake = Faker('fr_FR')

print(fake.sentences(5))
# ['Remarquer chant enfin cuisine intéresser journée.', 'Oublier émotion produire repousser pitié reste.', 'Habiter animer malheur.', 'Dangereux déposer magnifique vers vouloir situation public.', 'Reprendre fumée conseil face.']

print(fake.sentence(5))
# Énergie mensonge vivant présence liberté.

my_word_list = [
    'danish','cheesecake','sugar',
    'Lollipop','wafer','Gummies',
    'sesame','Jelly','beans',
    'pie','bar','Ice','oat' ]

# print(fake.sentence(ext_word_list=my_word_list))
# 'Oat beans oat Lollipop bar cheesecake.'