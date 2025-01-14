module default {

    type CommentInfo {
        required property comment_id -> str {
            constraint exclusive;
        };
        required property pull_request_id -> int64 {
            constraint exclusive;
        };
        required property creation_time -> datetime {
            default := datetime_current();
        }

        index on (.pull_request_id);
    }

    type Administrator {
        required property email -> str {
            constraint exclusive;
        }
    }

    type Agreement {
        required property name -> str {
            constraint exclusive;
        }

        property description -> str;

        required property creation_time -> datetime {
            default := datetime_current();
        }

        required property update_time -> datetime {
            default := datetime_current();
        }

        multi link versions -> AgreementVersion;
    }

    type AgreementVersion {

        required property current -> bool {
            default := False;
        }

        required property draft -> bool {
            default := true;
        }

        multi link texts -> AgreementText;

        required property creation_time -> datetime {
            default := datetime_current();
        }
    }

    type AgreementText {
        required property text -> str;

        required property title -> str {
            default := "";
        }

        required property culture -> str;

        required property update_time -> datetime {
            default := datetime_current();
        }

        required property creation_time -> datetime {
            default := datetime_current();
        }
    }

    type Repository {
        required property full_name -> str {
            constraint exclusive;
        };

        required link agreement -> Agreement;
    }

    type ContributorLicenseAgreement {
        required property email -> str {
            constraint exclusive;
        };
        index on (.email);

        property normalized_email := str_lower(.email);
        constraint exclusive on (.normalized_email);
        index on (.normalized_email);

        property username -> str;

        required property creation_time -> datetime {
            default := datetime_current();
        }

        required link agreement_version -> AgreementVersion;

        index on (.agreement_version);
    }
};
