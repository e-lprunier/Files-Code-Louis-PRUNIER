class UserProfile:
    def __init__(self, username, firstname="", lastname="", birthday=None, avatar=None):
        self.username = username
        self.firstname = firstname
        self.lastname = lastname
        self.birthday = birthday
        self.avatar = avatar

    def to_dict(self):
        return {
            "username": self.username,
            "firstname": self.firstname,
            "lastname": self.lastname,
            "birthday": self.birthday,
            "avatar": self.avatar
        }

    @staticmethod
    def from_dict(data):
        return UserProfile(
            username=data.get("username", ""),
            firstname=data.get("firstname", ""),
            lastname=data.get("lastname", ""),
            birthday=data.get("birthday"),
            avatar=data.get("avatar")
        )